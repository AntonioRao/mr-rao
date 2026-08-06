"""In-memory job store for async conversion with progress + cancel."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from config import JOB_TTL_SECONDS, MAX_JOBS_KEPT


@dataclass
class Job:
    id: str
    status: str = "pending"  # pending | running | done | error | cancelled
    progress: int = 0
    total: int = 1
    message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    cancel_flag: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def should_cancel(self) -> bool:
        return self.cancel_flag

    def set_progress(self, current: int, total: int, message: str = "") -> None:
        with self.lock:
            self.progress = current
            self.total = max(total, 1)
            self.message = message
            self.status = "running"

    def to_public(self) -> dict[str, Any]:
        with self.lock:
            pct = int(100 * self.progress / max(self.total, 1)) if self.total else 0
            return {
                "id": self.id,
                "status": self.status,
                "progress": self.progress,
                "total": self.total,
                "percent": min(100, pct),
                "message": self.message,
                "result": self.result if self.status == "done" else None,
                "error": self.error,
            }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._sweeper: threading.Thread | None = None

    def _ensure_sweeper(self) -> None:
        """Results (markdown + base64 attachments) used to sit in RAM forever
        when no new conversion arrived, because cleanup ran only in create()."""
        if self._sweeper is not None:
            return
        with self._lock:
            if self._sweeper is not None:
                return

            def _loop() -> None:
                while True:
                    time.sleep(60)
                    try:
                        self.cleanup()
                    except Exception:  # noqa: BLE001 — a sweeper must never die
                        pass

            self._sweeper = threading.Thread(
                target=_loop, daemon=True, name="mr-rao-job-sweeper"
            )
            self._sweeper.start()

    def create(self) -> Job:
        self.cleanup()
        self._ensure_sweeper()
        job = Job(id=uuid.uuid4().hex)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job:
            return False
        with job.lock:
            job.cancel_flag = True
            if job.status in ("pending", "running"):
                job.status = "cancelled"
                job.message = "Annullato dall'utente"
        return True

    def cleanup(self) -> None:
        """Drop expired jobs, then cap the store: a single result can hold a
        whole document plus base64 attachments."""
        now = time.time()
        with self._lock:
            for jid in [
                jid
                for jid, j in self._jobs.items()
                if now - j.created_at > JOB_TTL_SECONDS
            ]:
                del self._jobs[jid]

            if len(self._jobs) <= MAX_JOBS_KEPT:
                return
            # Evict the oldest *finished* jobs first; never a running one.
            finished = sorted(
                (j for j in self._jobs.values() if j.status in ("done", "error", "cancelled")),
                key=lambda j: j.created_at,
            )
            for job in finished:
                if len(self._jobs) <= MAX_JOBS_KEPT:
                    break
                del self._jobs[job.id]


job_store = JobStore()
