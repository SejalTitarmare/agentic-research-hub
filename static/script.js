const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const form = $("#form");
const topicInput = $("#topic");
const goBtn = $("#go");
const banner = $("#banner");
const empty = $("#empty");
const out = $("#out");
const tabs = $$(".tabs [role=tab]");
const steps = $$("#relay li");

const FILE_NAMES = {
  report: "research-report",
  feedback: "critic-feedback",
  search_results: "search-results",
  scraped_content: "scraped-content",
};

let source = null;
let timer = null;
let startedAt = 0;
let activeKey = "report";
let data = {};

/* ---------- helpers ---------- */

function renderMarkdown(md) {
  return DOMPurify.sanitize(marked.parse(md || ""));
}

function setStep(n, status, text) {
  const li = steps[n - 1];
  li.classList.remove("running", "done", "failed");
  if (status) li.classList.add(status);
  $(".state", li).textContent = text;
}

function resetRelay() {
  steps.forEach((_, i) => setStep(i + 1, null, "Waiting"));
}

function resetOutput() {
  data = {};
  tabs.forEach((t) => {
    t.disabled = true;
    t.setAttribute("aria-selected", "false");
  });
  $$(".prose").forEach((p) => {
    p.innerHTML = "";
    p.hidden = true;
  });
  out.hidden = true;
  banner.hidden = true;
}

function showTab(key) {
  activeKey = key;
  tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.key === key)));
  $$(".prose").forEach((p) => (p.hidden = p.id !== `pane-${key}`));
}

function startTimer(step) {
  stopTimer();
  startedAt = Date.now();
  const tick = () => {
    const s = Math.floor((Date.now() - startedAt) / 1000);
    setStep(step, "running", `Working… ${s}s`);
  };
  tick();
  timer = setInterval(tick, 1000);
}

function stopTimer() {
  clearInterval(timer);
  timer = null;
}

function setBusy(busy) {
  goBtn.disabled = busy;
  topicInput.disabled = busy;
  goBtn.textContent = busy ? "Researching…" : "Start research";
}

function showError(message) {
  banner.textContent = message;
  banner.hidden = false;
}

function finish() {
  if (source) source.close();
  source = null;
  stopTimer();
  setBusy(false);
}

/* ---------- run a research job ---------- */

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) return;

  if (source) source.close();
  resetRelay();
  resetOutput();
  empty.hidden = true;
  setBusy(true);

  let finished = false;
  source = new EventSource(`/api/research?topic=${encodeURIComponent(topic)}`);

  source.addEventListener("step", (ev) => {
    const { step } = JSON.parse(ev.data);
    startTimer(step);
  });

  source.addEventListener("result", (ev) => {
    const { step, key, content } = JSON.parse(ev.data);
    stopTimer();
    const secs = Math.floor((Date.now() - startedAt) / 1000);
    setStep(step, "done", `Done in ${secs}s`);

    data[key] = content;
    $(`#pane-${key}`).innerHTML = renderMarkdown(content);
    $(`#tab-${key}`).disabled = false;
    out.hidden = false;
    showTab(key); // show the newest output as it arrives
  });

  source.addEventListener("done", () => {
    finished = true;
    showTab("report");
    finish();
  });

  // Our own error event from app.py (named "failure" to avoid EventSource's built-in "error")
  source.addEventListener("failure", (ev) => {
    finished = true;
    const { step, message } = JSON.parse(ev.data);
    stopTimer();
    setStep(step, "failed", "Failed");
    showError(`The ${["search agent", "reader agent", "writer", "critic"][step - 1]} stopped with an error: ${message}`);
    finish();
  });

  // Network-level problem (server stopped, connection dropped)
  source.onerror = () => {
    if (finished) return;
    finished = true;
    stopTimer();
    $$("#relay li.running").forEach((li) => {
      li.classList.replace("running", "failed");
      $(".state", li).textContent = "Disconnected";
    });
    showError("Lost the connection to the server. Check that app.py is still running, then try again.");
    finish();
  };
});

/* ---------- tabs, copy, download ---------- */

tabs.forEach((t) => t.addEventListener("click", () => showTab(t.dataset.key)));

$("#copy").addEventListener("click", async (e) => {
  const btn = e.currentTarget;
  try {
    await navigator.clipboard.writeText(data[activeKey] || "");
    btn.textContent = "Copied";
  } catch {
    btn.textContent = "Copy failed";
  }
  setTimeout(() => (btn.textContent = "Copy"), 1500);
});

$("#download").addEventListener("click", () => {
  const blob = new Blob([data[activeKey] || ""], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${FILE_NAMES[activeKey]}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
});