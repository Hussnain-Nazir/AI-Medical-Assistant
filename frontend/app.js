/* ==========================================================================
   Cura - Dashboard application logic
   Plain JS, no build step. Talks to the FastAPI backend over fetch/XHR.
   ========================================================================== */

(() => {
  "use strict";

  const state = {
    apiBaseUrl: localStorage.getItem("cura.apiBaseUrl") || "http://localhost:8000",
    developerMode: localStorage.getItem("cura.developerMode") === "true",
    topK: parseInt(localStorage.getItem("cura.topK") || "5", 10),
    recentUploads: [],
    isSending: false,
  };

  // ---- Element references ----------------------------------------------

  const el = {
    sidebar: document.getElementById("sidebar"),
    sidebarBackdrop: document.getElementById("sidebarBackdrop"),
    menuToggle: document.getElementById("menuToggle"),

    dropzone: document.getElementById("dropzone"),
    browseBtn: document.getElementById("browseBtn"),
    fileInput: document.getElementById("fileInput"),
    uploadProgress: document.getElementById("uploadProgress"),
    uploadFilename: document.getElementById("uploadFilename"),
    uploadStatus: document.getElementById("uploadStatus"),
    progressFill: document.getElementById("progressFill"),

    docCount: document.getElementById("docCount"),
    docList: document.getElementById("docList"),
    recentList: document.getElementById("recentList"),

    dotGemini: document.getElementById("dotGemini"),
    valGemini: document.getElementById("valGemini"),
    dotChroma: document.getElementById("dotChroma"),
    valChroma: document.getElementById("valChroma"),
    dotConversation: document.getElementById("dotConversation"),
    valConversation: document.getElementById("valConversation"),
    dotReady: document.getElementById("dotReady"),
    valReady: document.getElementById("valReady"),
    statDocs: document.getElementById("statDocs"),
    statChunks: document.getElementById("statChunks"),

    reindexBtn: document.getElementById("reindexBtn"),
    clearDbBtn: document.getElementById("clearDbBtn"),

    devModeToggle: document.getElementById("devModeToggle"),
    topKInput: document.getElementById("topKInput"),
    apiBaseInput: document.getElementById("apiBaseInput"),

    chatScroll: document.getElementById("chatScroll"),
    chatInner: document.getElementById("chatInner"),
    emptyState: document.getElementById("emptyState"),
    composerInput: document.getElementById("composerInput"),
    sendBtn: document.getElementById("sendBtn"),
    clearChatBtn: document.getElementById("clearChatBtn"),
  };

  // ---- Init settings from storage ----------------------------------------

  el.devModeToggle.checked = state.developerMode;
  el.topKInput.value = state.topK;
  el.apiBaseInput.value = state.apiBaseUrl;

  // ---- Helpers -----------------------------------------------------------

  function apiUrl(path) {
    return `${state.apiBaseUrl.replace(/\/$/, "")}${path}`;
  }

  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function showToast(message, isError = false) {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      document.body.appendChild(stack);
    }
    const toast = document.createElement("div");
    toast.className = `toast${isError ? " error" : ""}`;
    toast.textContent = message;
    stack.appendChild(toast);
    setTimeout(() => toast.remove(), 4200);
  }

  async function safeJson(response) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  // ---- Sidebar toggle (mobile) --------------------------------------------

  function openSidebar() {
    el.sidebar.classList.add("open");
    el.sidebarBackdrop.classList.add("open");
  }

  function closeSidebar() {
    el.sidebar.classList.remove("open");
    el.sidebarBackdrop.classList.remove("open");
  }

  el.menuToggle.addEventListener("click", () => {
    el.sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
  });
  el.sidebarBackdrop.addEventListener("click", closeSidebar);

  // ---- Settings ------------------------------------------------------------

  el.devModeToggle.addEventListener("change", () => {
    state.developerMode = el.devModeToggle.checked;
    localStorage.setItem("cura.developerMode", state.developerMode);
  });

  el.topKInput.addEventListener("change", () => {
    const value = Math.min(20, Math.max(1, parseInt(el.topKInput.value, 10) || 5));
    state.topK = value;
    el.topKInput.value = value;
    localStorage.setItem("cura.topK", value);
  });

  el.apiBaseInput.addEventListener("change", () => {
    state.apiBaseUrl = el.apiBaseInput.value.trim() || "http://localhost:8000";
    localStorage.setItem("cura.apiBaseUrl", state.apiBaseUrl);
    refreshAll();
  });

  // ---- Health / status ------------------------------------------------------

  async function refreshHealth() {
    try {
      const response = await fetch(apiUrl("/health"), { method: "GET" });
      const data = await safeJson(response);
      if (!response.ok) throw new Error("unreachable");

      setDot(el.dotGemini, el.valGemini, data.gemini_configured, "Connected", "Not configured");
      setDot(el.dotChroma, el.valChroma, data.vector_store_reachable, "Connected", "Unreachable");
      setDot(
        el.dotConversation,
        el.valConversation,
        data.conversation_store_reachable,
        "Connected",
        "Unreachable"
      );
      setDot(el.dotReady, el.valReady, data.status === "ok", "Ready", "Degraded");

      el.statDocs.textContent = data.indexed_document_count ?? 0;
    } catch {
      setDot(el.dotGemini, el.valGemini, null, "", "Offline");
      setDot(el.dotChroma, el.valChroma, null, "", "Offline");
      setDot(el.dotConversation, el.valConversation, null, "", "Offline");
      setDot(el.dotReady, el.valReady, null, "", "Offline");
    }
  }

  function setDot(dotEl, valueEl, ok, okLabel, badLabel) {
    dotEl.classList.remove("ok", "warn", "down");
    if (ok === true) {
      dotEl.classList.add("ok");
      valueEl.textContent = okLabel;
    } else if (ok === false) {
      dotEl.classList.add("warn");
      valueEl.textContent = badLabel;
    } else {
      dotEl.classList.add("down");
      valueEl.textContent = badLabel;
    }
  }

  // ---- Documents -------------------------------------------------------------

  async function refreshDocuments() {
    try {
      const response = await fetch(apiUrl("/documents"), { method: "GET" });
      const data = await safeJson(response);
      if (!response.ok) throw new Error("failed");

      const documents = data.documents || [];
      el.docCount.textContent = documents.length;
      el.statDocs.textContent = data.total_documents ?? documents.length;
      el.statChunks.textContent = data.total_chunks ?? 0;

      if (documents.length === 0) {
        el.docList.innerHTML = '<p class="empty-note">No documents indexed yet.</p>';
        return;
      }

      el.docList.innerHTML = "";
      documents.forEach((doc) => {
        const card = document.createElement("div");
        card.className = "doc-card";
        card.innerHTML = `
          <div class="doc-card-top">
            <span class="doc-name">${escapeHtml(doc.filename)}</span>
            <button class="doc-remove" type="button">Remove</button>
          </div>
          <span class="doc-meta">${doc.page_count} page${doc.page_count === 1 ? "" : "s"} · ${doc.chunk_count} chunk${doc.chunk_count === 1 ? "" : "s"}</span>
        `;
        card.querySelector(".doc-remove").addEventListener("click", () => deleteDocument(doc.filename));
        el.docList.appendChild(card);
      });
    } catch {
      el.docList.innerHTML = '<p class="empty-note">Could not load documents. Check the API base URL.</p>';
    }
  }

  async function deleteDocument(filename) {
    try {
      const response = await fetch(apiUrl(`/documents/${encodeURIComponent(filename)}`), {
        method: "DELETE",
      });
      if (!response.ok) {
        const data = await safeJson(response);
        throw new Error(data.detail || "Delete failed.");
      }
      showToast(`Removed ${filename}.`);
      refreshDocuments();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  el.reindexBtn.addEventListener("click", async () => {
    el.reindexBtn.disabled = true;
    el.reindexBtn.textContent = "Re-indexing...";
    try {
      const response = await fetch(apiUrl("/reindex"), { method: "POST" });
      const data = await safeJson(response);
      if (!response.ok) throw new Error(data.detail || "Re-index failed.");
      showToast(`Re-indexed ${data.files_processed} document(s).`);
      refreshDocuments();
    } catch (err) {
      showToast(err.message, true);
    } finally {
      el.reindexBtn.disabled = false;
      el.reindexBtn.textContent = "Re-index all documents";
    }
  });

  el.clearDbBtn.addEventListener("click", async () => {
    const confirmed = window.confirm(
      "This removes every indexed document from the vector store. Continue?"
    );
    if (!confirmed) return;

    el.clearDbBtn.disabled = true;
    try {
      const response = await fetch(apiUrl("/documents"), { method: "DELETE" });
      const data = await safeJson(response);
      if (!response.ok) throw new Error(data.detail || "Clear failed.");
      showToast("Database cleared.");
      refreshDocuments();
    } catch (err) {
      showToast(err.message, true);
    } finally {
      el.clearDbBtn.disabled = false;
    }
  });

  // ---- Upload ---------------------------------------------------------------

  el.browseBtn.addEventListener("click", () => el.fileInput.click());

  el.fileInput.addEventListener("change", () => {
    if (el.fileInput.files.length > 0) {
      uploadFile(el.fileInput.files[0]);
      el.fileInput.value = "";
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    el.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      el.dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    el.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      el.dropzone.classList.remove("dragover");
    });
  });

  el.dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file) uploadFile(file);
  });

  function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      showToast("Only PDF files are accepted.", true);
      return;
    }

    el.uploadProgress.hidden = false;
    el.uploadFilename.textContent = file.name;
    el.uploadStatus.textContent = "Uploading";
    el.uploadStatus.classList.remove("is-success", "is-error");
    el.progressFill.classList.remove("indeterminate");
    el.progressFill.style.width = "0%";

    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl("/upload"));

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        el.progressFill.style.width = `${percent}%`;
      }
    };

    xhr.upload.onload = () => {
      el.uploadStatus.textContent = "Indexing";
      el.progressFill.classList.add("indeterminate");
    };

    xhr.onload = () => {
      el.progressFill.classList.remove("indeterminate");
      if (xhr.status === 201) {
        const data = JSON.parse(xhr.responseText);
        el.progressFill.style.width = "100%";
        el.uploadStatus.textContent = "Indexed";
        el.uploadStatus.classList.add("is-success");
        showToast(`Indexed ${data.filename}: ${data.chunks_created} chunks.`);
        addRecentUpload(data.filename);
        refreshDocuments();
      } else {
        let detail = "Upload failed.";
        try {
          detail = JSON.parse(xhr.responseText).detail || detail;
        } catch {
          /* ignore parse error */
        }
        el.uploadStatus.textContent = "Failed";
        el.uploadStatus.classList.add("is-error");
        showToast(detail, true);
      }
      setTimeout(() => {
        el.uploadProgress.hidden = true;
      }, 2400);
    };

    xhr.onerror = () => {
      el.progressFill.classList.remove("indeterminate");
      el.uploadStatus.textContent = "Connection error";
      el.uploadStatus.classList.add("is-error");
      showToast("Could not reach the backend API.", true);
    };

    xhr.send(formData);
  }

  function addRecentUpload(filename) {
    state.recentUploads.unshift({ filename, time: new Date() });
    state.recentUploads = state.recentUploads.slice(0, 5);
    renderRecentUploads();
  }

  function renderRecentUploads() {
    if (state.recentUploads.length === 0) {
      el.recentList.innerHTML = '<p class="empty-note">Nothing uploaded this session.</p>';
      return;
    }
    el.recentList.innerHTML = state.recentUploads
      .map(
        (item) =>
          `<div class="recent-item">${escapeHtml(item.filename)} · ${formatTime(item.time)}</div>`
      )
      .join("");
  }

  // ---- Chat -------------------------------------------------------------------

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }

  function hideEmptyState() {
    if (el.emptyState) {
      el.emptyState.remove();
    }
  }

  function appendUserMessage(text, timestamp) {
    hideEmptyState();
    const wrapper = document.createElement("div");
    wrapper.className = "message user";
    wrapper.innerHTML = `
      <div class="bubble"></div>
      <span class="message-timestamp">${formatTime(timestamp || new Date())}</span>
    `;
    wrapper.querySelector(".bubble").textContent = text;
    el.chatInner.appendChild(wrapper);
    scrollChatToBottom();
  }

  function appendTypingIndicator() {
    const wrapper = document.createElement("div");
    wrapper.className = "message assistant";
    wrapper.id = "typingIndicator";
    wrapper.innerHTML = `
      <div class="bubble typing-bubble">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    `;
    el.chatInner.appendChild(wrapper);
    scrollChatToBottom();
  }

  function removeTypingIndicator() {
    const indicator = document.getElementById("typingIndicator");
    if (indicator) indicator.remove();
  }

  // ---- Markdown rendering (self-contained, no external dependency) ----------
  //
  // Deliberately not using a CDN-hosted library here: this app previously
  // depended on marked.js + DOMPurify from cdnjs, which silently falls back
  // to plain, unrendered text if that CDN request is ever blocked (corporate
  // network, ad blocker, offline use). A small hand-rolled renderer removes
  // that failure mode entirely and keeps the app fully self-contained.
  //
  // Safety approach: every fragment of inline text is HTML-escaped first
  // (via escapeHtml), and only afterwards do we selectively reintroduce a
  // small fixed set of tags (<strong>, <em>, <code>, <h1-4>, <ul>/<li>,
  // <table>/<tr>/<th>/<td>, <hr>) generated entirely by this code -- never
  // from raw user/LLM input -- so there is no way for arbitrary HTML to be
  // injected.

  function renderInline(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+?)\*/g, "<em>$1</em>");
    html = html.replace(/`([^`]+?)`/g, "<code>$1</code>");
    return html;
  }

  function splitTableRow(line) {
    let trimmed = line.trim();
    if (trimmed.startsWith("|")) trimmed = trimmed.slice(1);
    if (trimmed.endsWith("|")) trimmed = trimmed.slice(0, -1);
    return trimmed.split("|").map((cell) => cell.trim());
  }

  function isTableSeparatorRow(line) {
    const trimmed = line.trim();
    if (!trimmed.includes("-")) return false;
    const cells = splitTableRow(trimmed);
    return cells.length > 0 && cells.every((cell) => /^:?-{1,}:?$/.test(cell));
  }

  function renderMarkdown(text) {
    const lines = String(text).replace(/\r\n/g, "\n").split("\n");
    let html = "";
    let paragraphLines = [];
    let listItems = [];

    function flushParagraph() {
      if (paragraphLines.length) {
        html += `<p>${renderInline(paragraphLines.join(" "))}</p>`;
        paragraphLines = [];
      }
    }

    function flushList() {
      if (listItems.length) {
        html += `<ul>${listItems.map((item) => `<li>${renderInline(item)}</li>`).join("")}</ul>`;
        listItems = [];
      }
    }

    let i = 0;
    while (i < lines.length) {
      const rawLine = lines[i];
      const line = rawLine.trim();

      if (line === "") {
        flushParagraph();
        flushList();
        i++;
        continue;
      }

      // GitHub-flavored pipe table: a row containing '|' immediately
      // followed by a valid "---" separator row.
      if (line.includes("|") && i + 1 < lines.length && isTableSeparatorRow(lines[i + 1])) {
        flushParagraph();
        flushList();

        const headerCells = splitTableRow(line);
        const bodyRows = [];
        i += 2; // skip header row + separator row

        while (i < lines.length && lines[i].trim() !== "" && lines[i].includes("|")) {
          bodyRows.push(splitTableRow(lines[i]));
          i++;
        }

        const theadHtml = `<thead><tr>${headerCells
          .map((cell) => `<th>${renderInline(cell)}</th>`)
          .join("")}</tr></thead>`;
        const tbodyHtml = `<tbody>${bodyRows
          .map((row) => `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join("")}</tr>`)
          .join("")}</tbody>`;
        html += `<div class="table-scroll"><table>${theadHtml}${tbodyHtml}</table></div>`;
        continue;
      }

      const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
      if (headingMatch) {
        flushParagraph();
        flushList();
        const level = headingMatch[1].length;
        html += `<h${level}>${renderInline(headingMatch[2])}</h${level}>`;
        i++;
        continue;
      }

      if (/^(\*{3,}|-{3,})$/.test(line)) {
        flushParagraph();
        flushList();
        html += "<hr>";
        i++;
        continue;
      }

      const listMatch = line.match(/^[-*]\s+(.*)$/);
      if (listMatch) {
        flushParagraph();
        listItems.push(listMatch[1]);
        i++;
        continue;
      }

      flushList();
      paragraphLines.push(line);
      i++;
    }

    flushParagraph();
    flushList();
    return html;
  }

  function appendAssistantMessage(answer, sources, retrievedChunks, timestamp) {
    const wrapper = document.createElement("div");
    wrapper.className = "message assistant";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = renderMarkdown(answer);
    wrapper.appendChild(bubble);

    const footer = document.createElement("div");
    footer.className = "message-footer";

    const messageTimestamp = document.createElement("span");
    messageTimestamp.className = "message-timestamp";
    messageTimestamp.textContent = formatTime(timestamp || new Date());
    footer.appendChild(messageTimestamp);

    let sourcesPanel = null;
    if (sources && sources.length > 0) {
      const toggleBtn = document.createElement("button");
      toggleBtn.type = "button";
      toggleBtn.className = "sources-toggle";
      toggleBtn.textContent = `Sources (${sources.length})`;
      footer.appendChild(toggleBtn);

      sourcesPanel = document.createElement("div");
      sourcesPanel.className = "sources-panel";
      sourcesPanel.hidden = true;
      sourcesPanel.innerHTML = `<p class="sources-heading">Sources</p><div class="source-cards"></div>`;
      const cardsContainer = sourcesPanel.querySelector(".source-cards");

      sources.forEach((source) => {
        const card = document.createElement("div");
        card.className = "source-card";
        const percent = Math.round(source.similarity_score * 100);
        card.innerHTML = `
          <span class="source-name">${escapeHtml(source.filename)}</span>
          <span class="source-page">p. ${source.page_number}</span>
          <span class="source-meter"><span class="source-meter-fill" style="width:${percent}%"></span></span>
        `;
        cardsContainer.appendChild(card);
      });

      toggleBtn.addEventListener("click", () => {
        const willOpen = sourcesPanel.hidden;
        sourcesPanel.hidden = !willOpen;
        toggleBtn.textContent = willOpen ? "Hide sources" : `Sources (${sources.length})`;
        if (willOpen) scrollChatToBottom();
      });
    }

    wrapper.appendChild(footer);
    if (sourcesPanel) wrapper.appendChild(sourcesPanel);

    if (retrievedChunks && retrievedChunks.length > 0) {
      const details = document.createElement("details");
      details.className = "chunks-details";
      const summary = document.createElement("summary");
      summary.textContent = `Retrieved chunks (${retrievedChunks.length})`;
      details.appendChild(summary);

      retrievedChunks.forEach((chunk) => {
        const item = document.createElement("div");
        item.className = "chunk-item";
        item.innerHTML = `
          <div class="chunk-item-meta">${escapeHtml(chunk.filename)} · page ${chunk.page_number} · similarity ${chunk.similarity_score}</div>
          <div class="chunk-item-text"></div>
        `;
        item.querySelector(".chunk-item-text").textContent = chunk.text;
        details.appendChild(item);
      });

      wrapper.appendChild(details);
    }

    el.chatInner.appendChild(wrapper);
    scrollChatToBottom();
  }

  function appendErrorMessage(message) {
    const wrapper = document.createElement("div");
    wrapper.className = "message assistant";
    wrapper.innerHTML = `<div class="bubble"></div>`;
    wrapper.querySelector(".bubble").textContent = message;
    el.chatInner.appendChild(wrapper);
    scrollChatToBottom();
  }

  function scrollChatToBottom() {
    requestAnimationFrame(() => {
      el.chatScroll.scrollTop = el.chatScroll.scrollHeight;
    });
  }

  async function sendMessage() {
    const question = el.composerInput.value.trim();
    if (!question || state.isSending) return;

    state.isSending = true;
    el.sendBtn.disabled = true;
    el.composerInput.value = "";
    autoResizeComposer();

    appendUserMessage(question);
    appendTypingIndicator();

    try {
      const response = await fetch(apiUrl("/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          top_k: state.topK,
          developer_mode: state.developerMode,
        }),
      });

      const data = await safeJson(response);
      removeTypingIndicator();

      if (!response.ok) {
        appendErrorMessage(data.detail || "Something went wrong reaching Cura.");
        return;
      }

      appendAssistantMessage(data.answer, data.sources, data.retrieved_chunks);
    } catch {
      removeTypingIndicator();
      appendErrorMessage("Could not reach the backend API. Check the API base URL in Settings.");
    } finally {
      state.isSending = false;
      el.sendBtn.disabled = false;
    }
  }

  el.sendBtn.addEventListener("click", sendMessage);

  el.composerInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  function autoResizeComposer() {
    el.composerInput.style.height = "auto";
    el.composerInput.style.height = `${Math.min(el.composerInput.scrollHeight, 160)}px`;
  }

  el.composerInput.addEventListener("input", autoResizeComposer);

  el.clearChatBtn.addEventListener("click", async () => {
    el.chatInner.innerHTML = `
      <div class="empty-state" id="emptyState">
        <p class="empty-state-title">Ask a question grounded in your documents</p>
        <p class="empty-state-sub">Cura answers only from what has been uploaded.<br>Informational use only - not professional medical advice.</p>
      </div>
    `;
    el.emptyState = document.getElementById("emptyState");

    try {
      const response = await fetch(apiUrl("/conversation"), { method: "DELETE" });
      if (!response.ok) {
        const data = await safeJson(response);
        throw new Error(data.detail || "Failed to clear the saved conversation.");
      }
    } catch (err) {
      showToast(
        err.message || "Could not clear the saved conversation on the server.",
        true
      );
    }
  });

  // ---- Conversation history (persisted server-side) --------------------------

  async function loadConversationHistory() {
    try {
      const response = await fetch(apiUrl("/conversation"), { method: "GET" });
      if (!response.ok) return;

      const data = await safeJson(response);
      const messages = data.messages || [];
      if (messages.length === 0) return;

      hideEmptyState();
      messages.forEach((message) => {
        const timestamp = message.created_at ? new Date(message.created_at) : new Date();
        if (message.role === "user") {
          appendUserMessage(message.content, timestamp);
        } else if (message.role === "assistant") {
          appendAssistantMessage(
            message.content,
            message.sources,
            message.retrieved_chunks,
            timestamp
          );
        }
      });
    } catch {
      // Backend unreachable at startup -- start with an empty conversation
      // in the UI; refreshHealth() will surface the outage separately.
    }
  }

  // ---- Bootstrap -----------------------------------------------------------

  function refreshAll() {
    refreshHealth();
    refreshDocuments();
  }

  loadConversationHistory();
  refreshAll();
  renderRecentUploads();
  setInterval(refreshHealth, 20000);
})();
