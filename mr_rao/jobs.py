"""In-memory job store for async conversion with progress + cancel."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from config import JOB_TTL_SECONDS


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

    def create(self) -> Job:
        self.cleanup()
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
        now = time.time()
        with self._lock:
            dead = [
                jid
                for jid, j in self._jobs.items()
                if now - j.created_at > JOB_TTL_SECONDS
            ]
            for jid in dead:
                del self._jobs[jid]


job_store = JobStore()
