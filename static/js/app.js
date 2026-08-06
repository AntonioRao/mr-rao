/**
 * Mr. Rao — frontend application
 */
(function () {
  "use strict";

  const MAX_BYTES = (window.MR_RAO_MAX_MB || 50) * 1024 * 1024;
  const POLL_MS = 400;

  const $ = (id) => document.getElementById(id);

  const els = {
    dropZone: $("drop-zone"),
    fileInput: $("file-input"),
    loading: $("loading"),
    loadingText: $("loading-text"),
    progressBar: $("progress-bar"),
    progressPct: $("progress-pct"),
    cancelBtn: $("cancel-btn"),
    resultCard: $("result-card"),
    markdownOut: $("markdown-output"),
    previewOut: $("preview-output"),
    copyBtn: $("copy-btn"),
    copyCleanBtn: $("copy-clean-btn"),
    downloadBtn: $("download-btn"),
    downloadTxtBtn: $("download-txt-btn"),
    toast: $("toast"),
    toastMsg: $("toast-msg"),
    toastIcon: $("toast-icon"),
    engineSelect: $("engine"),
    languageSelect: $("language"),
    privacyMaster: $("privacy-filter"),
    privacyPanel: $("privacy-panel"),
    includeTables: $("include-tables"),
    includeFrontmatter: $("include-frontmatter"),
    cleanOutput: $("clean-output"),
    mergeBatch: $("merge-batch"),
    tabRaw: $("tab-raw"),
    tabPreview: $("tab-preview"),
    redactionBadge: $("redaction-badge"),
    historyList: $("history-list"),
    queueList: $("queue-list"),
    batchBar: $("batch-bar"),
  };

  let currentMarkdown = "";
  let currentFilename = "documento";
  let currentJobId = null;
  let pollTimer = null;
  let abortPoll = false;
  const history = [];

  // ── Toast ──
  let toastTimer;
  function showToast(msg, type = "success") {
    clearTimeout(toastTimer);
    els.toastMsg.textContent = msg;
    els.toastIcon.textContent = type === "success" ? "✅" : "⚠️";
    els.toast.className = "toast show " + type;
    toastTimer = setTimeout(
      () => (els.toast.className = "toast " + type),
      type === "error" ? 6000 : 3000
    );
  }

  // ── Privacy panel toggle ──
  function syncPrivacyPanel() {
    if (!els.privacyPanel) return;
    els.privacyPanel.style.display = els.privacyMaster.checked ? "grid" : "none";
  }
  els.privacyMaster.addEventListener("change", syncPrivacyPanel);
  syncPrivacyPanel();

  // ── Tabs ──
  function showTab(which) {
    const raw = which === "raw";
    els.markdownOut.style.display = raw ? "block" : "none";
    els.previewOut.style.display = raw ? "none" : "block";
    els.tabRaw.classList.toggle("active", raw);
    els.tabPreview.classList.toggle("active", !raw);
  }
  els.tabRaw.addEventListener("click", () => showTab("raw"));
  els.tabPreview.addEventListener("click", () => showTab("preview"));

  // ── Minimal markdown → HTML (safe-ish) ──
  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderPreview(md) {
    // Strip YAML frontmatter for preview
    let body = md;
    if (body.startsWith("---")) {
      const end = body.indexOf("\n---", 3);
      if (end !== -1) body = body.slice(end + 4).replace(/^\n+/, "");
    }
    let html = escapeHtml(body);
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>");
    html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => "<ul>" + m + "</ul>");
    html = html.replace(/\n\n/g, "<br><br>");
    els.previewOut.innerHTML = html || "<em>Vuoto</em>";
  }

  function setResult(markdown, filename, redaction) {
    currentMarkdown = markdown || "";
    currentFilename = (filename || "documento").replace(/\.[^.]+$/, "");
    els.markdownOut.textContent = currentMarkdown;
    renderPreview(currentMarkdown);
    els.resultCard.style.display = "flex";
    if (els.redactionBadge) {
      const total = redaction && redaction.total ? redaction.total : 0;
      if (total > 0) {
        els.redactionBadge.style.display = "inline-flex";
        els.redactionBadge.textContent = `🛡️ ${total} redazioni`;
        els.redactionBadge.title = JSON.stringify(redaction.counts || {});
      } else {
        els.redactionBadge.style.display = "none";
      }
    }
    pushHistory(currentFilename, currentMarkdown, redaction);
    els.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
    showTab("raw");
  }

  function pushHistory(name, md, redaction) {
    history.unshift({
      name,
      md,
      redaction,
      at: new Date().toLocaleTimeString(),
    });
    if (history.length > 12) history.pop();
    renderHistory();
  }

  function renderHistory() {
    if (!els.historyList) return;
    if (!history.length) {
      els.historyList.innerHTML = '<p class="muted">Nessuna conversione in questa sessione.</p>';
      return;
    }
    els.historyList.innerHTML = history
      .map(
        (h, i) =>
          `<button type="button" class="history-item" data-idx="${i}">
            <span class="hi-name">${escapeHtml(h.name)}.md</span>
            <span class="hi-meta">${h.at}${h.redaction && h.redaction.total ? " · 🛡️" + h.redaction.total : ""}</span>
          </button>`
      )
      .join("");
    els.historyList.querySelectorAll(".history-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        const h = history[Number(btn.dataset.idx)];
        if (h) setResult(h.md, h.name + ".md", h.redaction);
      });
    });
  }
  renderHistory();

  function formPayload(extra = {}) {
    const fd = new FormData();
    fd.append("engine", els.engineSelect.value);
    fd.append("language", els.languageSelect.value);
    fd.append("privacy_filter", els.privacyMaster.checked);
    ["emails", "phones", "names", "fiscal", "amounts"].forEach((k) => {
      const el = $("privacy-" + k);
      if (el) fd.append("privacy_" + k, el.checked);
    });
    fd.append("privacy_scrubadub", "true");
    fd.append("include_tables", els.includeTables.checked);
    fd.append("include_frontmatter", els.includeFrontmatter.checked);
    fd.append("clean_output", els.cleanOutput.checked);
    Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
    return fd;
  }

  function setLoading(on, text) {
    els.loading.classList.toggle("active", on);
    if (text) els.loadingText.textContent = text;
    if (els.cancelBtn) els.cancelBtn.style.display = on ? "inline-flex" : "none";
    if (!on) {
      if (els.progressBar) els.progressBar.style.width = "0%";
      if (els.progressPct) els.progressPct.textContent = "";
    }
  }

  function updateProgress(pct, message) {
    if (els.progressBar) els.progressBar.style.width = Math.min(100, pct) + "%";
    if (els.progressPct) els.progressPct.textContent = pct ? pct + "%" : "";
    if (message) els.loadingText.textContent = message;
  }

  async function cancelJob() {
    abortPoll = true;
    if (currentJobId) {
      try {
        await fetch("/api/jobs/" + currentJobId + "/cancel", { method: "POST" });
      } catch (_) {}
    }
    currentJobId = null;
    setLoading(false);
    showToast("Conversione annullata", "error");
  }
  if (els.cancelBtn) els.cancelBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    cancelJob();
  });

  function pollJob(jobId) {
    return new Promise((resolve, reject) => {
      abortPoll = false;
      currentJobId = jobId;
      const tick = async () => {
        if (abortPoll) {
          reject(new Error("cancelled"));
          return;
        }
        try {
          const r = await fetch("/api/jobs/" + jobId);
          const d = await r.json();
          if (!r.ok) {
            reject(new Error(d.error || "Job non trovato"));
            return;
          }
          updateProgress(d.percent || 0, d.message || "Elaborazione…");
          if (d.status === "done") {
            currentJobId = null;
            resolve(d.result);
            return;
          }
          if (d.status === "error") {
            currentJobId = null;
            reject(new Error(d.error || "Errore conversione"));
            return;
          }
          if (d.status === "cancelled") {
            currentJobId = null;
            reject(new Error("cancelled"));
            return;
          }
          pollTimer = setTimeout(tick, POLL_MS);
        } catch (e) {
          reject(e);
        }
      };
      tick();
    });
  }

  function checkSize(file) {
    if (file.size > MAX_BYTES) {
      showToast(
        `File troppo grande (${(file.size / 1024 / 1024).toFixed(1)} MB). Max ${window.MR_RAO_MAX_MB || 50} MB.`,
        "error"
      );
      return false;
    }
    return true;
  }

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []).filter(Boolean);
    if (!files.length) return;
    for (const f of files) {
      if (!checkSize(f)) return;
    }

    const multi = files.length > 1;
    const merge = multi && els.mergeBatch && els.mergeBatch.checked;

    setLoading(true, multi ? `Batch: ${files.length} file…` : "Conversione in corso…");
    els.resultCard.style.display = "none";

    try {
      let jobId;
      if (multi) {
        const fd = formPayload({ merge: merge, merge_title: "Documento unificato" });
        files.forEach((f) => fd.append("files", f));
        const res = await fetch("/api/convert/batch", { method: "POST", body: fd });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || "Errore batch");
        jobId = body.job_id;
      } else {
        const fd = formPayload();
        fd.append("file", files[0]);
        const res = await fetch("/api/convert", { method: "POST", body: fd });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || "Errore conversione");
        jobId = body.job_id;
      }

      const result = await pollJob(jobId);
      setLoading(false);

      if (result.batch && result.items) {
        // show first, rest in history
        result.items.forEach((item, idx) => {
          if (item.error) {
            showToast(item.filename + ": " + item.error, "error");
            return;
          }
          if (idx === 0) setResult(item.markdown, item.filename, item.redaction);
          else pushHistory(item.filename.replace(/\.[^.]+$/, ""), item.markdown, item.redaction);
        });
        showToast(`${result.items.length} file convertiti`);
      } else {
        setResult(result.markdown, result.filename, result.redaction);
        showToast("Conversione completata");
      }
    } catch (e) {
      setLoading(false);
      if (e.message === "cancelled") return;
      showToast(e.message || "Impossibile contattare Mr. Rao. Verifica che il server sia avviato.", "error");
    }

    els.fileInput.value = "";
  }

  // Drop zone
  els.dropZone.addEventListener("click", (e) => {
    if (e.target.closest("button") || e.target.closest("input")) return;
    els.fileInput.click();
  });

  ["dragenter", "dragover"].forEach((ev) => {
    els.dropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      els.dropZone.classList.add("dragover");
    });
  });
  ["dragleave", "dragend"].forEach((ev) => {
    els.dropZone.addEventListener(ev, () => els.dropZone.classList.remove("dragover"));
  });
  els.dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    els.dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
  });
  els.fileInput.addEventListener("change", () => {
    if (els.fileInput.files.length) handleFiles(els.fileInput.files);
  });

  // Ctrl+V paste image
  document.addEventListener("paste", (e) => {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    for (const item of items) {
      if (item.type && item.type.startsWith("image/")) {
        e.preventDefault();
        const blob = item.getAsFile();
        if (!blob) return;
        const ext = (item.type.split("/")[1] || "png").replace("jpeg", "jpg");
        const file = new File([blob], `clipboard.${ext}`, { type: item.type });
        handleFiles([file]);
        showToast("Immagine incollata dagli appunti");
        return;
      }
    }
  });

  function stripFrontmatterAndNotes(md) {
    let body = md;
    if (body.startsWith("---")) {
      const end = body.indexOf("\n---", 3);
      if (end !== -1) body = body.slice(end + 4).replace(/^\n+/, "");
    }
    return body
      .replace(/<!--[\s\S]*?-->\n?/g, "")
      .replace(/^> 🛡️ \*.*$/gm, "")
      .replace(/^> ℹ️ \*.*$/gm, "")
      .trim();
  }

  els.copyBtn.addEventListener("click", () => {
    navigator.clipboard
      .writeText(currentMarkdown)
      .then(() => showToast("Copiato negli appunti!"))
      .catch(() => showToast("Impossibile copiare", "error"));
  });

  if (els.copyCleanBtn) {
    els.copyCleanBtn.addEventListener("click", () => {
      navigator.clipboard
        .writeText(stripFrontmatterAndNotes(currentMarkdown))
        .then(() => showToast("Copia pulita (per LLM) copiata!"))
        .catch(() => showToast("Impossibile copiare", "error"));
    });
  }

  function downloadBlob(content, filename, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: filename });
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  els.downloadBtn.addEventListener("click", () => {
    downloadBlob(currentMarkdown, currentFilename + ".md", "text/markdown;charset=utf-8");
    showToast("File .md scaricato!");
  });

  if (els.downloadTxtBtn) {
    els.downloadTxtBtn.addEventListener("click", () => {
      downloadBlob(
        stripFrontmatterAndNotes(currentMarkdown),
        currentFilename + ".txt",
        "text/plain;charset=utf-8"
      );
      showToast("File .txt scaricato!");
    });
  }
})();
