/**
 * Mr. Rao — frontend application
 */
(function () {
  "use strict";

  const MAX_MB = window.MR_RAO_MAX_MB || 50;
  const MAX_BYTES = MAX_MB * 1024 * 1024;
  const POLL_MS = 400;
  const RE_YAML_KEY = /^[A-Za-z_][A-Za-z0-9_-]*\s*:/;

  // ── Le due lingue, di qua ──
  // Le stringhe arrivano dallo stesso dizionario del server, in un blob
  // inline: un secondo elenco «solo per la pagina» sarebbe il posto dove
  // una traduzione manca senza che nessuno se ne accorga.
  const I18N = window.MR_RAO_I18N || {};

  /** Il testo nella lingua della pagina, coi segnaposto sostituiti.
   *
   * Una chiave che non esiste torna se stessa invece di dare `undefined`:
   * una stringa mancante deve produrre un'interfaccia brutta, non un
   * messaggio vuoto. Gemello di `t()` in mr_rao/i18n.py.
   *
   * La sostituzione usa split/join e non `String.replace`: dentro i campi
   * ci sono nomi di file, e in un rimpiazzo di `replace` un `$&` o un `$1`
   * verrebbero interpretati. */
  function t(chiave, campi) {
    let testo = I18N[chiave];
    if (testo === undefined) return chiave;
    if (campi) {
      for (const k in campi) testo = testo.split("{" + k + "}").join(campi[k]);
    }
    return testo;
  }

  /** Singolare e plurale, come `plurale()` in mr_rao/i18n.py.
   *  «1 redazioni» e' sbagliato in italiano quanto «1 redactions» in
   *  inglese, e la pagina lo scriveva in tre punti diversi. */
  function plurale(base, n) {
    let chiave = base + (n === 1 ? "_una" : "_molte");
    if (I18N[chiave] === undefined) chiave = base + (n === 1 ? "_uno" : "_molti");
    return t(chiave, { n: n });
  }

  /**
   * Remove the leading YAML block, if there really is one.
   * "starts with ---" is not enough: a document whose first line is a
   * horizontal rule would lose everything up to the next '---'.
   * Mirrors strip_frontmatter() in mr_rao/converter.py.
   */
  function stripFrontmatter(md) {
    if (!md || !md.startsWith("---")) return md;
    const lines = md.split("\n");
    if (lines.length < 3 || lines[0].trim() !== "---") return md;
    if (!RE_YAML_KEY.test(lines[1])) return md;
    for (let i = 1; i < lines.length; i++) {
      const t = lines[i].trim();
      if (t === "---" || t === "...") {
        return lines.slice(i + 1).join("\n").replace(/^\n+/, "");
      }
    }
    return md;
  }

  // Stesso elenco di privacy.FIELD_DEFAULTS lato Python. Un riconoscitore
  // che manca qui resta al suo valore predefinito: la casella nel pannello
  // c'e', ma non comanda niente.
  const PRIVACY_FIELDS = [
    "emails",
    "phones",
    "names",
    "name_guess",
    "addresses",
    "urls",
    "fiscal",
    "secrets",
    "dates",
    "amounts",
  ];

  const PROFILE_HINTS = {
    default: t("hint_profilo_default"),
    email_legali: t("hint_profilo_email_legali"),
    fatture: t("hint_profilo_fatture"),
    solo_ocr: t("hint_profilo_solo_ocr"),
    llm_ready: t("hint_profilo_llm_ready"),
    no_privacy: t("hint_profilo_no_privacy"),
  };

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
    diffOut: $("diff-output"),
    copyBtn: $("copy-btn"),
    copyCleanBtn: $("copy-clean-btn"),
    downloadBtn: $("download-btn"),
    downloadTxtBtn: $("download-txt-btn"),
    toast: $("toast"),
    toastMsg: $("toast-msg"),
    toastIcon: $("toast-icon"),
    engineSelect: $("engine"),
    // niente selettore lingua: il modello OCR è unico (alfabeti latini) e il
    // parametro non cambiava nulla — un comando che promette e non mantiene
    profileSelect: $("profile"),
    profileHint: $("profile-hint"),
    privacyMaster: $("privacy-filter"),
    privacyPanel: $("privacy-panel"),
    packPanel: $("pack-panel"),
    packIt: $("privacy-pack_it"),
    packEn: $("privacy-pack_en"),
    stile: $("privacy-stile"),
    includeTables: $("include-tables"),
    includeFrontmatter: $("include-frontmatter"),
    cleanOutput: $("clean-output"),
    mergeBatch: $("merge-batch"),
    compareMode: $("compare-mode"),
    includeRaw: $("include-raw"),
    tabRaw: $("tab-raw"),
    tabPreview: $("tab-preview"),
    tabDiff: $("tab-diff"),
    redactionBadge: $("redaction-badge"),
    historyList: $("history-list"),
    attachmentsBar: $("attachments-bar"),
    watchInbox: $("watch-inbox"),
    watchOutbox: $("watch-outbox"),
    watchMove: $("watch-move"),
    watchStart: $("watch-start"),
    watchStop: $("watch-stop"),
    watchStatus: $("watch-status"),
    watchBrowseInbox: $("watch-browse-inbox"),
    watchBrowseOutbox: $("watch-browse-outbox"),
  };

  let currentMarkdown = "";
  let currentRaw = null;
  let currentFilename = "documento";
  let currentJobId = null;
  let abortPoll = false;
  const history = [];

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

  function syncPrivacyPanel() {
    if (!els.privacyPanel) return;
    const on = els.privacyMaster.checked;
    els.privacyPanel.style.display = on ? "grid" : "none";
    // I pacchetti seguono l'interruttore generale: a filtro spento non c'e'
    // niente da scegliere, e due caselle accese sopra un filtro spento
    // sarebbero solo un modo per credersi protetti.
    if (els.packPanel) els.packPanel.style.display = on ? "grid" : "none";
    const offHint = $("privacy-off-hint");
    if (offHint) offHint.style.display = on ? "none" : "block";
  }
  els.privacyMaster.addEventListener("change", syncPrivacyPanel);
  syncPrivacyPanel();

  if (els.profileSelect) {
    els.profileSelect.addEventListener("change", () => {
      const id = els.profileSelect.value;
      if (els.profileHint) els.profileHint.textContent = PROFILE_HINTS[id] || "";
      // Soft-apply known profile defaults to checkboxes
      const map = {
        default: { privacy: true, tables: true, fm: true, clean: false, ocr: false },
        email_legali: { privacy: true, tables: false, fm: true, clean: true, ocr: false },
        fatture: { privacy: true, tables: true, fm: true, clean: false, ocr: false },
        solo_ocr: { privacy: false, tables: true, fm: false, clean: true, ocr: true },
        llm_ready: { privacy: true, tables: true, fm: false, clean: true, ocr: false },
        no_privacy: { privacy: false, tables: true, fm: true, clean: false, ocr: false },
      };
      const m = map[id];
      if (!m) return;
      els.privacyMaster.checked = m.privacy;
      els.includeTables.checked = m.tables;
      els.includeFrontmatter.checked = m.fm;
      els.cleanOutput.checked = m.clean;
      if (m.ocr) els.engineSelect.value = "rapidocr";
      else if (id !== "solo_ocr") els.engineSelect.value = "auto";
      syncPrivacyPanel();
    });
  }

  function showTab(which) {
    const raw = which === "raw";
    const prev = which === "preview";
    const diff = which === "diff";
    els.markdownOut.style.display = raw ? "block" : "none";
    els.previewOut.style.display = prev ? "block" : "none";
    if (els.diffOut) els.diffOut.style.display = diff ? "block" : "none";
    els.tabRaw.classList.toggle("active", raw);
    els.tabPreview.classList.toggle("active", prev);
    if (els.tabDiff) els.tabDiff.classList.toggle("active", diff);
  }
  els.tabRaw.addEventListener("click", () => showTab("raw"));
  els.tabPreview.addEventListener("click", () => showTab("preview"));
  if (els.tabDiff) els.tabDiff.addEventListener("click", () => showTab("diff"));

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderPreview(md) {
    let html = escapeHtml(stripFrontmatter(md));
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>");
    html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => "<ul>" + m + "</ul>");
    html = html.replace(/\n\n/g, "<br><br>");
    els.previewOut.innerHTML = html || "<em>" + escapeHtml(t("js_vuoto")) + "</em>";
  }

  function renderDiff(raw, scrubbed) {
    if (!els.diffOut) return;
    if (!raw) {
      els.diffOut.textContent = t("js_no_raw");
      return;
    }
    // Highlight placeholders in scrubbed view vs note raw length
    const scrubbedEsc = escapeHtml(scrubbed || "");
    const highlighted = scrubbedEsc.replace(
      /\{\{[A-Z0-9_]+\}\}/g,
      '<mark style="background:rgba(239,68,68,0.35);color:#fecaca;padding:0 2px;border-radius:3px">$&</mark>'
    );
    els.diffOut.innerHTML =
      '<div style="margin-bottom:0.75rem;color:var(--text-2);font-size:0.8rem">' +
      escapeHtml(
        t("js_diff_intestazione", { prima: raw.length, dopo: (scrubbed || "").length })
      ) +
      "</div>" +
      '<pre style="white-space:pre-wrap;font:inherit;margin:0;color:#c9d5f0">' +
      highlighted +
      "</pre>" +
      '<hr style="border:none;border-top:1px solid var(--border);margin:1rem 0">' +
      '<div style="font-size:0.75rem;color:var(--text-3);margin-bottom:0.35rem">' +
      escapeHtml(t("js_diff_originale")) +
      "</div>" +
      '<pre style="white-space:pre-wrap;font:inherit;margin:0;color:#94a3b8;max-height:240px;overflow:auto">' +
      escapeHtml(raw) +
      "</pre>";
  }

  function renderAttachments(list) {
    if (!els.attachmentsBar) return;
    if (!list || !list.length) {
      els.attachmentsBar.style.display = "none";
      els.attachmentsBar.innerHTML = "";
      return;
    }
    els.attachmentsBar.style.display = "flex";
    els.attachmentsBar.innerHTML =
      `<span class="muted" style="width:100%">${escapeHtml(t("js_allegati_email"))}</span>` +
      list
        .map((a, i) => {
          if (a.skipped) {
            const etichetta = t("js_allegato_saltato", {
              nome: a.filename,
              motivo: a.reason || t("js_allegato_troppo_grande"),
            });
            return `<span class="fmt-badge">${escapeHtml(etichetta)}</span>`;
          }
          return `<button type="button" class="btn" data-att="${i}">📎 ${escapeHtml(a.filename)} (${(a.size / 1024).toFixed(1)} KB)</button>`;
        })
        .join("");
    els.attachmentsBar._data = list;
    els.attachmentsBar.querySelectorAll("[data-att]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const att = list[Number(btn.dataset.att)];
        if (!att || !att.content_base64) return;
        const bin = atob(att.content_base64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        const blob = new Blob([bytes], { type: att.mime || "application/octet-stream" });
        const url = URL.createObjectURL(blob);
        const a = Object.assign(document.createElement("a"), {
          href: url,
          download: att.filename || "allegato.bin",
        });
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        showToast(t("js_allegato_scaricato", { nome: att.filename }));
      });
    });
  }

  // record=false when re-opening an entry from the history, otherwise viewing
  // an old conversion would push a copy of it back onto the list every click.
  function setResult(markdown, filename, redaction, extra, record) {
    extra = extra || {};
    if (record === undefined) record = true;
    currentMarkdown = markdown || "";
    currentRaw = extra.markdown_raw || null;
    currentFilename = (filename || "documento").replace(/\.[^.]+$/, "");
    els.markdownOut.textContent = currentMarkdown;
    renderPreview(currentMarkdown);
    renderDiff(currentRaw, currentMarkdown);
    renderAttachments(extra.attachments || []);
    els.resultCard.style.display = "flex";
    if (els.tabDiff) {
      els.tabDiff.style.display = currentRaw ? "inline-flex" : "none";
    }
    if (els.redactionBadge) {
      const total = redaction && redaction.total ? redaction.total : 0;
      const sospetti = (redaction && redaction.suspects) || [];
      if (total > 0 || sospetti.length > 0) {
        els.redactionBadge.style.display = "inline-flex";
        // «1 redazioni» e «1 redactions» erano sbagliati entrambi: il numero
        // lo sceglie l'utente caricando il file, e capita spesso che sia 1.
        // Due parti, non una stringa sola: i sospetti vanno in ambra perche'
        // chiedono di fare qualcosa, mentre le redazioni riuscite sono
        // lavoro finito. Nodi di testo e non innerHTML -- qui passano
        // conteggi, ma questo e' il programma sbagliato in cui prendere
        // l'abitudine di incollare stringhe nel DOM.
        els.redactionBadge.replaceChildren();
        els.redactionBadge.classList.toggle("ha-sospetti", sospetti.length > 0);
        // «1 redazioni» e «1 redactions» erano sbagliati entrambi: il numero
        // lo sceglie l'utente caricando il file, e capita spesso che sia 1.
        els.redactionBadge.append("🛡️ " + plurale("redazioni", total));
        if (sospetti.length) {
          const parte = document.createElement("span");
          parte.className = "badge-sospetti";
          parte.textContent = " · ⚠️ " + plurale("sospetti", sospetti.length);
          els.redactionBadge.append(parte);
        }
        // I sospetti sono il motivo per cui questo riquadro esiste: "3
        // redazioni" da solo non distingue un documento pulito da un
        // documento che il riconoscitore non ha saputo leggere.
        els.redactionBadge.title = sospetti.length
          ? sospetti.map((s) => `${s.sample} — ${s.why}`).join("\n")
          : JSON.stringify(redaction.counts || {});
      } else {
        els.redactionBadge.style.display = "none";
      }
    }
    if (record) pushHistory(currentFilename, currentMarkdown, redaction, extra);
    els.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
    showTab("raw");
  }

  function pushHistory(name, md, redaction, extra) {
    history.unshift({ name, md, redaction, extra, at: new Date().toLocaleTimeString() });
    if (history.length > 12) history.pop();
    renderHistory();
  }

  function renderHistory() {
    if (!els.historyList) return;
    if (!history.length) {
      els.historyList.innerHTML =
        '<p class="muted">' + escapeHtml(t("sessione_vuota")) + "</p>";
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
        if (h) setResult(h.md, h.name + ".md", h.redaction, h.extra || {}, false);
      });
    });
  }
  renderHistory();

  function formPayload(extra) {
    extra = extra || {};
    const fd = new FormData();
    // La lingua della pagina viaggia col lavoro: il testo che Mr. Rao scrive
    // *dentro* il Markdown (intestazioni email, «Tabelle estratte», l'avviso
    // sull'OCR) deve uscire nella lingua che l'utente sta guardando.
    fd.append("lang", document.documentElement.lang || "it");
    if (els.profileSelect) fd.append("profile", els.profileSelect.value);
    fd.append("engine", els.engineSelect.value);
    fd.append("privacy_filter", els.privacyMaster.checked);
    PRIVACY_FIELDS.forEach((k) => {
      const el = $("privacy-" + k);
      if (el) fd.append("privacy_" + k, el.checked);
    });
    // I pacchetti non stanno in PRIVACY_FIELDS: quelli dicono *quali dati*
    // nascondere, questi *di quale Paese*. Sono due domande diverse, e
    // mescolarle vorrebbe dire che spegnere i telefoni spegne anche l'IBAN.
    if (els.packIt) fd.append("privacy_pack_it", els.packIt.checked);
    if (els.packEn) fd.append("privacy_pack_en", els.packEn.checked);
    // Tri-stato: vuoto = automatico, e «non lo so» non e’ «e’ un modulo».
    if (els.stile) fd.append("privacy_stile", els.stile.value);
    fd.append("include_tables", els.includeTables.checked);
    fd.append("include_frontmatter", els.includeFrontmatter.checked);
    fd.append("clean_output", els.cleanOutput.checked);
    fd.append("include_raw", els.includeRaw ? els.includeRaw.checked : true);
    Object.keys(extra).forEach((k) => fd.append(k, extra[k]));
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
    showToast(t("err_annullata"), "error");
  }
  if (els.cancelBtn)
    els.cancelBtn.addEventListener("click", (e) => {
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
            reject(new Error(d.error || t("err_job_assente")));
            return;
          }
          updateProgress(d.percent || 0, d.message || t("js_elaborazione"));
          if (d.status === "done") {
            currentJobId = null;
            resolve(d.result);
            return;
          }
          if (d.status === "error") {
            currentJobId = null;
            reject(new Error(d.error || t("err_conversione")));
            return;
          }
          if (d.status === "cancelled") {
            currentJobId = null;
            reject(new Error("cancelled"));
            return;
          }
          setTimeout(tick, POLL_MS);
        } catch (e) {
          reject(e);
        }
      };
      tick();
    });
  }

  function mb(bytes) {
    return (bytes / 1024 / 1024).toFixed(1);
  }

  /** The server limit applies to the whole request, so check the total too:
   *  3 files of 20 MB each pass a per-file check and then get a 413. */
  function checkSize(files) {
    for (const f of files) {
      if (f.size > MAX_BYTES) {
        showToast(
          t("js_file_troppo_grande", { nome: f.name, mb: mb(f.size), max: MAX_MB }),
          "error"
        );
        return false;
      }
    }
    const total = files.reduce((sum, f) => sum + f.size, 0);
    if (total > MAX_BYTES) {
      showToast(
        t("js_invio_troppo_grande", { mb: mb(total), max: MAX_MB }),
        "error"
      );
      return false;
    }
    return true;
  }

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []).filter(Boolean);
    // Clear the input straight away: the File objects stay valid, and every
    // early return below would otherwise leave the same file selected, so
    // re-picking it would not fire "change" and the app would look stuck.
    els.fileInput.value = "";
    if (!files.length) return;
    if (!checkSize(files)) return;

    const multi = files.length > 1;
    const compare = els.compareMode && els.compareMode.checked;
    const merge = (multi && els.mergeBatch && els.mergeBatch.checked) || compare;

    if (compare && files.length !== 2) {
      showToast(t("err_confronto_due_file"), "error");
      return;
    }

    setLoading(
      true,
      multi
        ? t("js_batch_in_corso", { n: files.length })
        : t("conversione_in_corso")
    );
    els.resultCard.style.display = "none";

    try {
      let jobId;
      if (multi || compare) {
        // Niente merge_title: il titolo predefinito lo scrive il server, nella
        // lingua del lavoro. Mandarlo da qui significava che il server doveva
        // riconoscerlo *per valore* per capire se era una scelta o il default
        // — e bastava tradurlo perche' smettesse di funzionare.
        const fd = formPayload({ merge: merge, compare: compare });
        files.forEach((f) => fd.append("files", f));
        const res = await fetch("/api/convert/batch", { method: "POST", body: fd });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || t("err_batch"));
        jobId = body.job_id;
      } else {
        const fd = formPayload();
        fd.append("file", files[0]);
        const res = await fetch("/api/convert", { method: "POST", body: fd });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || t("err_conversione"));
        jobId = body.job_id;
      }

      const result = await pollJob(jobId);
      setLoading(false);

      if (result.batch && result.items) {
        result.items.forEach((item, idx) => {
          if (item.error) {
            showToast(item.filename + ": " + item.error, "error");
            return;
          }
          if (idx === 0)
            setResult(item.markdown, item.filename, item.redaction, {
              markdown_raw: item.markdown_raw,
              attachments: item.attachments,
            });
          else
            pushHistory(item.filename.replace(/\.[^.]+$/, ""), item.markdown, item.redaction, {
              markdown_raw: item.markdown_raw,
              attachments: item.attachments,
            });
        });
        showToast(plurale("file_convertiti", result.items.length));
      } else {
        setResult(result.markdown, result.filename, result.redaction, {
          markdown_raw: result.markdown_raw,
          attachments: result.attachments,
        });
        // Le chiavi restano letterali dentro `t(...)`: e' cosi' che il test
        // che le raccoglie dal sorgente riesce a vederle.
        showToast(compare ? t("js_confronto_completato") : t("js_conversione_completata"));
      }
    } catch (e) {
      setLoading(false);
      if (e.message === "cancelled") return;
      // "Failed to fetch" non vuol dire quasi mai che il server e' spento.
      // Il caso di gran lunga piu' frequente e' che il browser non sia
      // riuscito a *leggere* il file: succede ogni volta che il documento e'
      // aperto in Word o Excel, che lo tengono bloccato. Il messaggio
      // generico mandava a cercare il problema nel server, che sta benissimo
      // — e l'utente non ha modo di indovinare.
      const nonLeggibile =
        e instanceof TypeError || /failed to fetch|network|NotReadable/i.test(e.message || "");
      showToast(
        nonLeggibile
          ? t("err_file_non_leggibile")
          : e.message || t("err_server_irraggiungibile"),
        "error"
      );
    }
  }

  els.dropZone.addEventListener("click", (e) => {
    if (e.target.closest("button") || e.target.closest("input")) return;
    els.fileInput.click();
  });

  // The drop zone advertises role="button" and is focusable, so it has to be
  // operable from the keyboard too, not just with the mouse.
  els.dropZone.addEventListener("keydown", (e) => {
    if (e.target !== els.dropZone) return;
    if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
      e.preventDefault();
      els.fileInput.click();
    }
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

  document.addEventListener("paste", (e) => {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    for (const item of items) {
      if (item.type && item.type.startsWith("image/")) {
        e.preventDefault();
        const blob = item.getAsFile();
        if (!blob) return;
        const ext = (item.type.split("/")[1] || "png").replace("jpeg", "jpg");
        const file = new File([blob], "clipboard." + ext, { type: item.type });
        handleFiles([file]);
        showToast(t("js_immagine_incollata"));
        return;
      }
    }
  });

  // Scandisce una volta sola invece di usare /<!--[\s\S]*?-->/g. Su un
  // documento pieno di "<!--" mai chiusi quel pattern riparte da ogni
  // apertura e arriva ogni volta in fondo: tempo quadratico, e qui vuol dire
  // la scheda del browser che si pianta. Stesso ragionamento del gemello in
  // converter.py, che e' l'unico posto dove questo testo viene poi *usato*.
  function togliCommentiHtml(testo) {
    let fuori = "";
    let i = 0;
    for (;;) {
      const inizio = testo.indexOf("<!--", i);
      if (inizio === -1) return fuori + testo.slice(i);
      const fine = testo.indexOf("-->", inizio + 4);
      if (fine === -1) return fuori + testo.slice(i);
      fuori += testo.slice(i, inizio);
      i = fine + 3;
      if (testo[i] === "\n") i += 1;
    }
  }

  function stripFrontmatterAndNotes(md) {
    return togliCommentiHtml(stripFrontmatter(md))
      .replace(/^> 🛡️ \*.*$/gm, "")
      .replace(/^> ℹ️ \*.*$/gm, "")
      .trim();
  }

  function toBase64Utf8(str) {
    return btoa(unescape(encodeURIComponent(str)));
  }

  function setupDragOut(el) {
    if (!el) return;
    el.addEventListener("dragstart", (e) => {
      if (!currentMarkdown) {
        e.preventDefault();
        return;
      }
      const name = currentFilename + ".md";
      const mime = "text/markdown";
      const b64 = toBase64Utf8(currentMarkdown);
      // Chrome / Edge desktop drag-out
      e.dataTransfer.setData("DownloadURL", mime + ":" + name + ":" + "data:" + mime + ";base64," + b64);
      e.dataTransfer.setData("text/plain", currentMarkdown);
      e.dataTransfer.effectAllowed = "copy";
    });
  }
  setupDragOut(els.downloadBtn);
  setupDragOut(els.markdownOut);

  els.copyBtn.addEventListener("click", () => {
    navigator.clipboard
      .writeText(currentMarkdown)
      .then(() => showToast(t("js_copiato")))
      .catch(() => showToast(t("js_copia_fallita"), "error"));
  });

  if (els.copyCleanBtn) {
    els.copyCleanBtn.addEventListener("click", () => {
      navigator.clipboard
        .writeText(stripFrontmatterAndNotes(currentMarkdown))
        .then(() => showToast(t("js_copiato_pulito")))
        .catch(() => showToast(t("js_copia_fallita"), "error"));
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
    showToast(t("js_md_scaricato"));
  });

  if (els.downloadTxtBtn) {
    els.downloadTxtBtn.addEventListener("click", () => {
      downloadBlob(
        stripFrontmatterAndNotes(currentMarkdown),
        currentFilename + ".txt",
        "text/plain;charset=utf-8"
      );
      showToast(t("js_txt_scaricato"));
    });
  }

  // ── Tooltip ──
  // Un solo elemento riposizionato: niente attributo title, che compare dopo
  // un secondo, non si può stilare e non appare col focus da tastiera.
  (function setupTooltips() {
    const tip = $("tip");
    if (!tip) return;
    let target = null;

    function place() {
      if (!target) return;
      const r = target.getBoundingClientRect();
      const t = tip.getBoundingClientRect();
      const margine = 8;
      let left = r.left + r.width / 2 - t.width / 2;
      left = Math.max(margine, Math.min(left, window.innerWidth - t.width - margine));
      // sopra l'elemento; se non ci sta, sotto
      let top = r.top - t.height - margine;
      if (top < margine) top = r.bottom + margine;
      tip.style.left = left + "px";
      tip.style.top = top + "px";
    }

    function show(el) {
      const testo = el.getAttribute("data-tip");
      if (!testo) return;
      target = el;
      // innerHTML voluto: sei tooltip contengono <b>. La sorgente e' sempre un
      // attributo scritto nei template, mai testo che arriva da un documento
      // convertito -- quello passa da escapeHtml() prima di toccare il DOM.
      // Se un giorno un data-tip venisse popolato da dati, qui va textContent.
      tip.innerHTML = testo;
      tip.classList.add("show");
      tip.setAttribute("aria-hidden", "false");
      place();
    }

    function hide() {
      target = null;
      tip.classList.remove("show");
      tip.setAttribute("aria-hidden", "true");
    }

    function trova(e) {
      return e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
    }

    document.addEventListener("mouseover", (e) => {
      const el = trova(e);
      if (el && el !== target) show(el);
      else if (!el && target) hide();
    });
    document.addEventListener("focusin", (e) => {
      const el = trova(e);
      if (el) show(el);
    });
    document.addEventListener("focusout", hide);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") hide();
    });
    window.addEventListener("scroll", hide, true);
    window.addEventListener("resize", hide);
  })();

  // ── Watch + cartelle predefinite Documenti\Mr Rao\… ──
  async function loadDefaultFolders(force) {
    try {
      // POST: crea le cartelle se mancano. La GET è in sola lettura, perché
      // una GET non deve modificare il disco.
      const r = await fetch("/api/folders/defaults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const d = await r.json();
      if (!r.ok || !d.ok) return d;
      if (els.watchInbox && (force || !els.watchInbox.value)) {
        els.watchInbox.value = d.inbox || "";
      }
      if (els.watchOutbox && (force || !els.watchOutbox.value)) {
        els.watchOutbox.value = d.outbox || "";
      }
      const hint = $("watch-defaults-hint");
      if (hint && d.inbox && d.outbox) {
        let html =
          "Predefinite: <code>" +
          escapeHtml(d.inbox) +
          "</code> → <code>" +
          escapeHtml(d.outbox) +
          "</code>";
        // Se i Documenti sono sincronizzati col cloud le cartelle finiscono
        // altrove: va detto, perché contraddirebbe la promessa "zero cloud".
        if (d.reason && /cloud/i.test(d.reason)) {
          html += '<br><span class="warn-note">⚠️ ' + escapeHtml(d.reason) + ".</span>";
        }
        hint.innerHTML = html;
      }
      return d;
    } catch (_) {
      return null;
    }
  }

  async function browseFolderInto(inputEl, title) {
    if (!inputEl) return;
    try {
      const r = await fetch("/api/folders/browse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initial: inputEl.value || undefined,
          title: title || t("js_scegli_cartella"),
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || t("js_sfoglia_non_disponibile"));
      if (d.cancelled || !d.path) {
        showToast(t("js_nessuna_cartella"));
        return;
      }
      inputEl.value = d.path;
      showToast(t("js_cartella_impostata"));
    } catch (e) {
      showToast(e.message || t("js_sfoglia_fallita"), "error");
    }
  }

  async function refreshWatch() {
    try {
      const r = await fetch("/api/watch");
      const d = await r.json();
      if (els.watchStatus) {
        const convertiti = plurale("file_convertiti", d.processed || 0);
        els.watchStatus.textContent = d.running
          ? t("js_in_ascolto") + " · " + (d.message || "") + " · " + convertiti
          : d.message || t("watch_non_attiva");
      }
      if (d.running) {
        if (els.watchInbox && d.inbox) els.watchInbox.value = d.inbox;
        if (els.watchOutbox && d.outbox) els.watchOutbox.value = d.outbox;
      } else if (d.defaults) {
        if (els.watchInbox && !els.watchInbox.value) els.watchInbox.value = d.defaults.inbox || "";
        if (els.watchOutbox && !els.watchOutbox.value) els.watchOutbox.value = d.defaults.outbox || "";
      }
    } catch (_) {}
  }

  if (els.watchBrowseInbox) {
    els.watchBrowseInbox.addEventListener("click", () =>
      browseFolderInto(els.watchInbox, t("watch_inbox_etichetta"))
    );
  }
  if (els.watchBrowseOutbox) {
    els.watchBrowseOutbox.addEventListener("click", () =>
      browseFolderInto(els.watchOutbox, t("watch_outbox_etichetta"))
    );
  }

  if (els.watchStart) {
    els.watchStart.addEventListener("click", async () => {
      let inbox = els.watchInbox.value.trim();
      let outbox = els.watchOutbox.value.trim();
      if (!inbox || !outbox) {
        const defs = await loadDefaultFolders(true);
        inbox = (els.watchInbox.value || (defs && defs.inbox) || "").trim();
        outbox = (els.watchOutbox.value || (defs && defs.outbox) || "").trim();
      }
      if (!inbox || !outbox) {
        showToast(t("js_scegli_cartelle"), "error");
        return;
      }
      try {
        const r = await fetch("/api/watch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            inbox,
            outbox,
            move_done: els.watchMove && els.watchMove.checked,
            profile: els.profileSelect ? els.profileSelect.value : "default",
            // Anche il monitoraggio scrive documenti: la lingua che parte da
            // qui e' quella che vedra' chi apre i .md della cartella di uscita.
            lang: document.documentElement.lang || "it",
            interval: 2,
          }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || t("err_watch_fallito"));
        showToast(t("js_monitoraggio_attivo"));
        refreshWatch();
      } catch (e) {
        showToast(e.message, "error");
      }
    });
  }
  if (els.watchStop) {
    els.watchStop.addEventListener("click", async () => {
      await fetch("/api/watch", { method: "DELETE" });
      showToast(t("js_monitoraggio_disattivo"));
      refreshWatch();
    });
  }
  loadDefaultFolders(true).then(() => refreshWatch());
  setInterval(refreshWatch, 4000);
})();
