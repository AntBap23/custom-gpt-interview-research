const STORAGE_KEY = "active-study-id";
const PAGE_LABELS = {
  home: "Home",
  dashboard: "Dashboard",
  studies: "Studies",
  workspace: "Workspace",
  protocol: "Protocol",
  personas: "Personas",
  "interview-guide": "Interview Guide",
  transcripts: "Transcripts",
  simulations: "Simulations",
  comparisons: "Comparisons",
  settings: "Settings",
  "sign-in": "Sign In",
};

const TOP_NAV = [
  { key: "home", label: "Home", href: "/" },
  { key: "dashboard", label: "Dashboard", href: "/dashboard" },
  { key: "studies", label: "Studies", href: "/studies" },
  { key: "workspace", label: "Workspace", href: "/workspace" },
  { key: "settings", label: "Settings", href: "/settings" },
  { key: "sign-in", label: "Sign In", href: "/sign-in" },
];

const WORKSPACE_NAV = [
  { key: "workspace", label: "Overview", href: "/workspace" },
  { key: "protocol", label: "Protocol", href: "/protocol" },
  { key: "personas", label: "Personas", href: "/personas" },
  { key: "interview-guide", label: "Interview Guide", href: "/interview-guide" },
  { key: "transcripts", label: "Transcripts", href: "/transcripts" },
  { key: "simulations", label: "Simulations", href: "/simulations" },
  { key: "comparisons", label: "Comparisons", href: "/comparisons" },
];

const WORKSPACE_PAGES = new Set(WORKSPACE_NAV.map((item) => item.key));
const PUBLIC_PAGES = new Set(["home", "sign-in"]);
const state = {
  studies: [],
  activeStudyId: localStorage.getItem(STORAGE_KEY) || "",
  extractedQuestions: [],
  auth: {
    authenticated: false,
    user: null,
  },
};

const page = document.body.dataset.page || "home";

function el(tagName, options = {}) {
  const node = document.createElement(tagName);
  if (options.className) node.className = options.className;
  if (options.text) node.textContent = options.text;
  if (options.html) node.innerHTML = options.html;
  if (options.attrs) {
    Object.entries(options.attrs).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== false) {
        node.setAttribute(key, value === true ? "" : value);
      }
    });
  }
  return node;
}

function pretty(value) {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function bodyReady() {
  requestAnimationFrame(() => document.body.classList.add("is-ready"));
}

function installPageTransitions() {
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link) return;
    const url = new URL(link.href, window.location.origin);
    if (url.origin !== window.location.origin) return;
    if (link.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey) return;
    if (url.pathname === window.location.pathname) return;
    event.preventDefault();
    document.body.classList.add("is-transitioning");
    window.setTimeout(() => {
      window.location.assign(url.pathname + url.search + url.hash);
    }, 140);
  });
}

function installCardSpotlight() {
  const targets = document.querySelectorAll(".panel-card, .showcase-card, .metric-card, .resource-card, .report-block");
  targets.forEach((node) => {
    node.addEventListener("pointermove", (event) => {
      const rect = node.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      node.style.setProperty("--mx", `${x}px`);
      node.style.setProperty("--my", `${y}px`);
      node.style.setProperty("--glow", "1");
    });
    node.addEventListener("pointerleave", () => {
      node.style.setProperty("--glow", "0");
    });
  });
}

async function callApi(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const isFormData = options.body instanceof FormData;
  if (!isFormData && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = text;
  }

  if (!response.ok) {
    throw new Error(typeof data === "string" ? data : pretty(data));
  }
  return data;
}

async function loadAuthSession() {
  try {
    const session = await callApi("/api/auth/session");
    state.auth.authenticated = Boolean(session?.authenticated);
    state.auth.user = session?.user || null;
  } catch {
    state.auth.authenticated = false;
    state.auth.user = null;
  }
}

function currentStudy() {
  return state.studies.find((study) => study.id === state.activeStudyId) || null;
}

function setActiveStudyId(studyId) {
  state.activeStudyId = studyId || "";
  localStorage.setItem(STORAGE_KEY, state.activeStudyId);
}

function scopedPath(path) {
  if (!state.activeStudyId) return path;
  const url = new URL(path, window.location.origin);
  url.searchParams.set("study_id", state.activeStudyId);
  return `${url.pathname}${url.search}`;
}

function formatDate(value) {
  if (!value) return "Unknown date";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function setNodeContent(node, content) {
  if (!node) return;
  node.textContent = typeof content === "string" ? content : pretty(content);
}

function makeEmptyNote(message) {
  return el("div", { className: "empty-note", text: message });
}

function createMetaPills(items) {
  const row = el("div", { className: "meta-row" });
  items.forEach((item) => row.appendChild(el("span", { className: "pill", text: item })));
  return row;
}

async function signOutCurrentSession() {
  try {
    await callApi("/api/auth/sign-out", { method: "POST" });
  } catch (error) {
    console.error("Sign out request failed", error);
  } finally {
    state.auth.authenticated = false;
    state.auth.user = null;
    setActiveStudyId("");
    window.location.assign("/sign-in");
  }
}

function renderHeader() {
  const header = document.querySelector("[data-site-header]");
  if (!header) return;

  const bar = el("div", { className: "header-bar" });
  const brand = el("a", { className: "brand", attrs: { href: "/" } });
  brand.appendChild(el("span", { className: "brand__kicker", text: "Qualitative Research Platform" }));
  brand.appendChild(el("strong", { className: "brand__title", text: "Qualitative AI Interview Studio" }));
  brand.appendChild(
    el("span", {
      className: "brand__copy",
      text: "A multi-page research workspace for studies, simulations, and comparison review.",
    }),
  );

  const nav = el("nav", { className: "primary-nav", attrs: { "aria-label": "Primary navigation" } });
  TOP_NAV.forEach((item) => {
    const link = el("a", {
      className: `primary-nav__link${isTopNavActive(item.key) ? " is-active" : ""}`,
      text: item.label,
      attrs: { href: item.href },
    });
    nav.appendChild(link);
  });

  const utility = el("div", { className: "header-utility" });
  const switcher = el("div", { className: "study-switcher" });
  const selectLabel = el("label");
  selectLabel.appendChild(el("span", { className: "field-label", text: "Active Study" }));
  const select = el("select", { attrs: { id: "global-study-select" } });
  select.appendChild(el("option", { text: "All studies / unscoped", attrs: { value: "" } }));
  state.studies.forEach((study) => {
    select.appendChild(el("option", { text: study.name, attrs: { value: study.id } }));
  });
  select.value = state.activeStudyId;
  select.addEventListener("change", () => {
    setActiveStudyId(select.value);
    window.location.reload();
  });
  selectLabel.appendChild(select);
  switcher.appendChild(selectLabel);

  const account = el("div", { className: "account-chip" });
  account.appendChild(el("span", { className: "field-label", text: "Account" }));
  account.appendChild(el("strong", { text: state.auth.authenticated ? state.auth.user?.email || "Signed in" : "Not signed in" }));
  account.appendChild(
    el("span", {
      className: "brand__copy",
      text: state.auth.authenticated ? "Session active for this browser." : "Sign in to access study operations.",
    }),
  );
  if (state.auth.authenticated) {
    const signOutButton = el("button", {
      className: "button button--secondary account-chip__action",
      text: "Sign out",
      attrs: { type: "button" },
    });
    signOutButton.addEventListener("click", async () => {
      await signOutCurrentSession();
    });
    account.appendChild(signOutButton);
  } else {
    const signInLink = el("a", { className: "text-link", text: "Sign in", attrs: { href: "/sign-in" } });
    account.appendChild(signInLink);
  }

  utility.append(switcher, account);
  bar.append(brand, nav, utility);
  header.replaceChildren(bar);
}

function renderWorkspaceNav() {
  const nav = document.querySelector("[data-workspace-nav]");
  if (!nav) return;
  WORKSPACE_NAV.forEach((item) => {
    nav.appendChild(
      el("a", {
        className: `workspace-nav__link${page === item.key ? " is-active" : ""}`,
        text: item.label,
        attrs: { href: item.href },
      }),
    );
  });
}

function isTopNavActive(key) {
  if (key === "workspace") return WORKSPACE_PAGES.has(page);
  return page === key;
}

function requireActiveStudy(containerId, message) {
  if (currentStudy()) return false;
  const node = document.getElementById(containerId);
  if (node) {
    node.replaceChildren(makeEmptyNote(message));
  }
  return true;
}

function renderResourceCards(container, items, formatter) {
  container.replaceChildren();
  if (!items.length) {
    container.appendChild(makeEmptyNote("No records found in the current scope."));
    return;
  }
  items.forEach((item) => container.appendChild(formatter(item)));
}

function resourceCard(title, bodyText, pills = []) {
  const card = el("article", { className: "resource-card" });
  card.appendChild(el("h3", { text: title }));
  if (bodyText) card.appendChild(el("p", { text: bodyText }));
  if (pills.length) card.appendChild(createMetaPills(pills));
  return card;
}

async function loadStudies() {
  state.studies = await callApi("/api/studies");
  if (state.activeStudyId && !state.studies.some((study) => study.id === state.activeStudyId)) {
    setActiveStudyId("");
  }
}

async function loadCollection(name) {
  return callApi(scopedPath(`/api/${name}`));
}

async function initDashboard() {
  const [protocols, personas, simulations, comparisons] = await Promise.all([
    loadCollection("protocols"),
    loadCollection("personas"),
    loadCollection("simulations"),
    loadCollection("comparisons"),
  ]);

  setNodeContent(document.getElementById("dashboard-studies-count"), state.studies.length);
  setNodeContent(document.getElementById("dashboard-protocols-count"), protocols.length);
  setNodeContent(document.getElementById("dashboard-personas-count"), personas.length);
  setNodeContent(document.getElementById("dashboard-simulations-count"), simulations.length);

  const active = currentStudy();
  setNodeContent(document.getElementById("dashboard-active-study"), active ? active.name : "No study selected");
  setNodeContent(
    document.getElementById("dashboard-active-study-copy"),
    active ? active.description || "This study is currently active across the app." : "Select a study from the top bar to scope dashboard summaries and workflow links.",
  );

  const readiness = document.getElementById("dashboard-readiness");
  readiness.replaceChildren(
    resourceCard("Protocol coverage", protocols.length ? `${protocols.length} protocol record(s)` : "No protocol records yet."),
    resourceCard("Persona coverage", personas.length ? `${personas.length} persona record(s)` : "No personas created yet."),
    resourceCard("Comparison readiness", simulations.length ? "Simulations exist and can be compared." : "Run simulations to unlock comparison work."),
  );

  const collections = document.getElementById("dashboard-collections");
  collections.replaceChildren(
    resourceCard("Comparisons", `${comparisons.length} saved comparison record(s)`),
    resourceCard("Recent simulations", simulations[0] ? `Most recent simulation created ${formatDate(simulations[0].created_at)}.` : "No simulations yet."),
  );
}

async function initStudies() {
  const portfolioCount = document.getElementById("studies-portfolio-count");
  const portfolioCopy = document.getElementById("studies-portfolio-copy");
  const activeCard = document.getElementById("active-study-card");
  const list = document.getElementById("study-list");

  setNodeContent(portfolioCount, `${state.studies.length} ${state.studies.length === 1 ? "study" : "studies"} loaded`);
  setNodeContent(
    portfolioCopy,
    state.studies.length
      ? "Select an active study from the top bar or the list below to scope the rest of the platform."
      : "Create a study to start building a structured workflow around a specific research question.",
  );

  const active = currentStudy();
  activeCard.replaceChildren(
    active
      ? resourceCard(active.name, active.description || "No description added yet.", [
          `Created ${formatDate(active.created_at)}`,
          "Current active study",
        ])
      : makeEmptyNote("No study selected yet."),
  );

  renderResourceCards(list, state.studies, (study) => {
    const card = resourceCard(study.name, study.description || "No description added yet.", [
      `Created ${formatDate(study.created_at)}`,
      study.id === state.activeStudyId ? "Active study" : "Available",
    ]);
    const button = el("button", {
      className: "button button--secondary",
      text: study.id === state.activeStudyId ? "Selected" : "Set active study",
      attrs: { type: "button" },
    });
    button.addEventListener("click", () => {
      setActiveStudyId(study.id);
      window.location.reload();
    });
    card.appendChild(button);
    return card;
  });

  const form = document.getElementById("study-create-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const output = document.getElementById("study-create-output");
    const formData = new FormData(form);
    const payload = {
      name: String(formData.get("name") || "").trim(),
      description: String(formData.get("description") || "").trim(),
    };

    try {
      const record = await callApi("/api/studies", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setActiveStudyId(record.id);
      setNodeContent(output, `Created study: ${record.name}`);
      await loadStudies();
      renderHeader();
      await initStudies();
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });
}

async function initWorkspace() {
  const title = document.getElementById("workspace-title");
  const copy = document.getElementById("workspace-copy");
  const stage = document.getElementById("workspace-stage");
  const stageCopy = document.getElementById("workspace-stage-copy");
  const workflow = document.getElementById("workspace-workflow");

  if (!currentStudy()) {
    workflow.replaceChildren(makeEmptyNote("Select a study from the top bar to unlock workspace details."));
    return;
  }

  const [protocols, personas, guides, comparisons] = await Promise.all([
    loadCollection("protocols"),
    loadCollection("personas"),
    loadCollection("question-guides"),
    loadCollection("comparisons"),
  ]);

  title.textContent = currentStudy().name;
  copy.textContent = currentStudy().description || "This study is now the active workspace for protocol, asset, and comparison work.";

  let stageText = "Protocol setup";
  let stageBody = "Define the protocol that should guide the rest of the workflow.";
  if (protocols.length && (!personas.length || !guides.length)) {
    stageText = "Asset preparation";
    stageBody = "The protocol exists. Prepare personas and the shared guide next.";
  } else if (protocols.length && personas.length && guides.length && !comparisons.length) {
    stageText = "Ready for simulation and comparison";
    stageBody = "Core study assets exist. You can move into simulation and comparative review.";
  } else if (comparisons.length) {
    stageText = "Analysis in progress";
    stageBody = "Comparison records already exist for this study.";
  }

  stage.textContent = stageText;
  stageCopy.textContent = stageBody;

  setNodeContent(document.getElementById("workspace-protocol-count"), protocols.length);
  setNodeContent(document.getElementById("workspace-persona-count"), personas.length);
  setNodeContent(document.getElementById("workspace-guide-count"), guides.length);
  setNodeContent(document.getElementById("workspace-comparison-count"), comparisons.length);

  workflow.replaceChildren(
    resourceCard("1. Protocol", protocols.length ? `${protocols.length} protocol record(s) saved.` : "No protocol yet."),
    resourceCard("2. Personas and guide", personas.length && guides.length ? "Both are available." : "Prepare personas and the shared guide."),
    resourceCard("3. Comparison work", comparisons.length ? `${comparisons.length} comparison record(s) saved.` : "No comparisons generated yet."),
  );
}

async function initProtocols() {
  if (requireActiveStudy("protocol-list", "Select a study before saving or viewing protocol records.")) return;
  const list = document.getElementById("protocol-list");
  const output = document.getElementById("protocol-output");
  const form = document.getElementById("protocol-form");
  const uploadForm = document.getElementById("protocol-upload-form");
  const sourceText = form?.querySelector('textarea[name="source_text"]');
  const sharedContext = form?.querySelector('textarea[name="shared_context"]');

  async function refresh() {
    const protocols = await loadCollection("protocols");
    renderResourceCards(list, protocols, (protocol) =>
      resourceCard(protocol.name, protocol.analysis_focus || "No analysis focus provided.", [formatDate(protocol.created_at)]),
    );
  }

  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(uploadForm);
    const file = formData.get("file");
    if (!(file instanceof File) || !file.name) {
      setNodeContent(output, "Choose a protocol document before uploading.");
      return;
    }

    const payload = new FormData();
    payload.append("file", file);

    try {
      const extracted = await callApi("/api/protocols/extract-upload", {
        method: "POST",
        body: payload,
      });
      if (sourceText) {
        sourceText.value = extracted.text || "";
      }
      if (sharedContext && !sharedContext.value.trim()) {
        sharedContext.value = extracted.text || "";
      }
      setNodeContent(output, `Loaded protocol text from ${file.name}. Review and split it across the protocol fields as needed.`);
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      name: String(formData.get("name") || "").trim(),
      shared_context: String(formData.get("shared_context") || "").trim(),
      interview_style_guidance: String(formData.get("interview_style_guidance") || "").trim(),
      consistency_rules: String(formData.get("consistency_rules") || "").trim(),
      analysis_focus: String(formData.get("analysis_focus") || "").trim(),
      study_id: state.activeStudyId,
    };

    try {
      const record = await callApi("/api/protocols", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setNodeContent(output, `Saved protocol: ${record.name}`);
      await refresh();
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  await refresh();
}

async function initPersonas() {
  if (requireActiveStudy("persona-list", "Select a study before creating or viewing personas.")) return;
  const list = document.getElementById("persona-list");
  const output = document.getElementById("persona-output");
  const form = document.getElementById("persona-form");
  const uploadForm = document.getElementById("persona-upload-form");
  const personaText = form?.querySelector('textarea[name="text"]');

  async function refresh() {
    const personas = await loadCollection("personas");
    renderResourceCards(list, personas, (persona) =>
      resourceCard(persona.name, `${persona.job || "Participant role"} • ${persona.education || "Education not specified"}`, [
        persona.personality || "No personality note",
      ]),
    );
  }

  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(uploadForm);
    const file = formData.get("file");
    if (!(file instanceof File) || !file.name) {
      setNodeContent(output, "Choose a document before uploading.");
      return;
    }

    const payload = new FormData();
    payload.append("file", file);

    try {
      const extracted = await callApi("/api/personas/extract-upload", {
        method: "POST",
        body: payload,
      });
      if (personaText) {
        personaText.value = extracted.text || "";
      }
      setNodeContent(output, `Loaded text from ${file.name}. Review it, then extract the persona.`);
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const extracted = await callApi("/api/personas/extract", {
        method: "POST",
        body: JSON.stringify({
          text: String(formData.get("text") || ""),
          suggested_name: String(formData.get("suggested_name") || "").trim() || null,
        }),
      });
      const saved = await callApi("/api/personas", {
        method: "POST",
        body: JSON.stringify({ ...extracted, study_id: state.activeStudyId }),
      });
      setNodeContent(output, `Saved persona: ${saved.name}`);
      await refresh();
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  await refresh();
}

async function initInterviewGuide() {
  if (requireActiveStudy("guide-list", "Select a study before creating or viewing interview guides.")) return;
  const questionsOutput = document.getElementById("questions-output");
  const list = document.getElementById("guide-list");
  const extractForm = document.getElementById("questions-form");
  const saveForm = document.getElementById("guide-save-form");
  const uploadForm = document.getElementById("guide-upload-form");
  const guideText = extractForm?.querySelector('textarea[name="text"]');

  async function refresh() {
    const guides = await loadCollection("question-guides");
    renderResourceCards(list, guides, (guide) =>
      resourceCard(guide.name, `${guide.questions.length} question(s)`, [formatDate(guide.created_at)]),
    );
  }

  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(uploadForm);
    const file = formData.get("file");
    if (!(file instanceof File) || !file.name) {
      setNodeContent(questionsOutput, "Choose a guide document before uploading.");
      return;
    }

    const payload = new FormData();
    payload.append("file", file);

    try {
      const extracted = await callApi("/api/question-guides/extract-upload", {
        method: "POST",
        body: payload,
      });
      if (guideText) {
        guideText.value = extracted.text || "";
      }
      setNodeContent(questionsOutput, `Loaded text from ${file.name}. Review it, then extract questions.`);
    } catch (error) {
      setNodeContent(questionsOutput, error.message);
    }
  });

  extractForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(extractForm);
    try {
      const questions = await callApi("/api/question-guides/extract", {
        method: "POST",
        body: JSON.stringify({
          text: String(formData.get("text") || ""),
          improve_with_ai: formData.get("improve_with_ai") === "on",
        }),
      });
      state.extractedQuestions = questions;
      setNodeContent(questionsOutput, questions.length ? questions.map((item, index) => `${index + 1}. ${item}`).join("\n") : "No questions extracted.");
    } catch (error) {
      setNodeContent(questionsOutput, error.message);
    }
  });

  saveForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(saveForm);
    if (!state.extractedQuestions.length) {
      setNodeContent(questionsOutput, "Extract questions before saving a guide.");
      return;
    }
    try {
      await callApi("/api/question-guides", {
        method: "POST",
        body: JSON.stringify({
          name: String(formData.get("name") || "").trim(),
          questions: state.extractedQuestions,
          study_id: state.activeStudyId,
        }),
      });
      setNodeContent(questionsOutput, "Guide saved successfully.");
      await refresh();
    } catch (error) {
      setNodeContent(questionsOutput, error.message);
    }
  });

  await refresh();
}

async function initTranscripts() {
  if (requireActiveStudy("transcript-list", "Select a study before saving or viewing transcripts.")) return;
  const list = document.getElementById("transcript-list");
  const output = document.getElementById("transcript-output");
  const form = document.getElementById("transcript-form");
  const uploadForm = document.getElementById("transcript-upload-form");
  const transcriptText = form?.querySelector('textarea[name="content"]');
  const transcriptName = form?.querySelector('input[name="name"]');

  async function refresh() {
    const transcripts = await loadCollection("transcripts");
    renderResourceCards(list, transcripts, (transcript) =>
      resourceCard(transcript.name, `${transcript.content.slice(0, 180)}${transcript.content.length > 180 ? "..." : ""}`, [
        transcript.source_type || "text",
      ]),
    );
  }

  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(uploadForm);
    const file = formData.get("file");
    if (!(file instanceof File) || !file.name) {
      setNodeContent(output, "Choose a transcript document before uploading.");
      return;
    }

    const payload = new FormData();
    payload.append("file", file);

    try {
      const extracted = await callApi("/api/transcripts/extract-upload", {
        method: "POST",
        body: payload,
      });
      if (transcriptText) {
        transcriptText.value = extracted.text || "";
      }
      if (transcriptName && !transcriptName.value.trim()) {
        transcriptName.value = file.name.replace(/\.[^.]+$/, "");
      }
      setNodeContent(output, `Loaded text from ${file.name}. Review it, then save the transcript.`);
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const record = await callApi("/api/transcripts", {
        method: "POST",
        body: JSON.stringify({
          name: String(formData.get("name") || "").trim(),
          content: String(formData.get("content") || "").trim(),
          source_type: "uploaded_or_text",
          study_id: state.activeStudyId,
        }),
      });
      setNodeContent(output, `Saved transcript: ${record.name}`);
      await refresh();
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  await refresh();
}

function populateSelect(node, items, labelKey = "name", includeBlank = true) {
  if (!node) return;
  node.replaceChildren();
  if (includeBlank) {
    node.appendChild(el("option", { text: "Select an option", attrs: { value: "" } }));
  }
  items.forEach((item) => {
    node.appendChild(el("option", { text: item[labelKey], attrs: { value: item.id } }));
  });
}

async function initSimulations() {
  if (requireActiveStudy("simulation-list", "Select a study before running or viewing simulations.")) return;
  const [personas, guides, protocols] = await Promise.all([
    loadCollection("personas"),
    loadCollection("question-guides"),
    loadCollection("protocols"),
  ]);

  populateSelect(document.getElementById("simulation-persona-select"), personas);
  populateSelect(document.getElementById("simulation-guide-select"), guides);
  populateSelect(document.getElementById("simulation-protocol-select"), protocols);

  const form = document.getElementById("simulation-form");
  const output = document.getElementById("simulation-output");
  const list = document.getElementById("simulation-list");

  async function refresh() {
    const simulations = await loadCollection("simulations");
    renderResourceCards(list, simulations, (simulation) => {
      const card = resourceCard(
        `Simulation ${simulation.id.slice(0, 8)}`,
        `${simulation.responses.length} response(s) captured`,
        [formatDate(simulation.created_at)],
      );
      const exportsRow = el("div", { className: "meta-row" });
      ["txt", "docx", "pdf", "html", "csv"].forEach((fileType) => {
        exportsRow.appendChild(
          el("a", {
            className: "text-link",
            text: `Export ${fileType.toUpperCase()}`,
            attrs: { href: `/api/simulations/${simulation.id}/exports/${fileType}` },
          }),
        );
      });
      card.appendChild(exportsRow);
      return card;
    });
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await callApi("/api/simulations", {
        method: "POST",
        body: JSON.stringify({
          persona_id: String(formData.get("persona_id") || ""),
          question_guide_id: String(formData.get("question_guide_id") || ""),
          protocol_id: String(formData.get("protocol_id") || "") || null,
          study_id: state.activeStudyId,
        }),
      });
      setNodeContent(output, `Simulation created with ${result.responses.length} responses.`);
      await refresh();
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  await refresh();
}

function renderComparisonReport(container, payload) {
  container.replaceChildren();
  if (!payload || typeof payload !== "object") {
    container.appendChild(makeEmptyNote("No comparison payload available."));
    return;
  }

  const overview = payload.overview || {};
  container.appendChild(resourceCard("Key takeaway", overview.key_takeaway || "No overview available."));

  const table = payload.comparison_table || [];
  if (table.length) {
    const tableNode = el("table", { className: "comparison-table" });
    tableNode.innerHTML = `
      <thead>
        <tr>
          <th>Theme</th>
          <th>Real Pattern</th>
          <th>AI Pattern</th>
          <th>Difference</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = tableNode.querySelector("tbody");
    table.forEach((row) => {
      const tr = el("tr");
      [row.theme, row.real_pattern, row.ai_pattern, row.difference].forEach((value) => {
        tr.appendChild(el("td", { text: value || "" }));
      });
      tbody.appendChild(tr);
    });
    container.appendChild(tableNode);
  }

  if (payload.markdown_report) {
    const block = el("div", { className: "report-block" });
    block.appendChild(el("h3", { text: "Narrative report" }));
    block.appendChild(el("p", { text: payload.markdown_report }));
    container.appendChild(block);
  }
}

async function initComparisons() {
  if (requireActiveStudy("comparison-list", "Select a study before generating or viewing comparisons.")) return;
  const [transcripts, simulations, protocols] = await Promise.all([
    loadCollection("transcripts"),
    loadCollection("simulations"),
    loadCollection("protocols"),
  ]);

  populateSelect(document.getElementById("comparison-transcript-select"), transcripts);
  populateSelect(document.getElementById("comparison-simulation-select"), simulations, "id");
  populateSelect(document.getElementById("comparison-protocol-select"), protocols);

  const form = document.getElementById("comparison-form");
  const output = document.getElementById("comparison-output");
  const report = document.getElementById("comparison-report");
  const list = document.getElementById("comparison-list");

  async function refresh() {
    const comparisons = await loadCollection("comparisons");
    renderResourceCards(list, comparisons, (comparison) =>
      resourceCard(`Comparison ${comparison.id.slice(0, 8)}`, comparison.payload?.overview?.key_takeaway || "No summary available.", [
        formatDate(comparison.created_at),
      ]),
    );
    if (comparisons[0]) {
      renderComparisonReport(report, comparisons[0].payload);
    }
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const result = await callApi("/api/comparisons", {
        method: "POST",
        body: JSON.stringify({
          transcript_id: String(formData.get("transcript_id") || ""),
          simulation_id: String(formData.get("simulation_id") || ""),
          protocol_id: String(formData.get("protocol_id") || "") || null,
          study_id: state.activeStudyId,
        }),
      });
      setNodeContent(output, "Comparison generated successfully.");
      renderComparisonReport(report, result.payload);
      await refresh();
    } catch (error) {
      setNodeContent(output, error.message);
    }
  });

  await refresh();
}

async function initSettings() {
  const stateNode = document.getElementById("settings-state");
  if (stateNode) {
    stateNode.replaceChildren(
      resourceCard("Current page", PAGE_LABELS[page] || page),
      resourceCard("Auth session", state.auth.authenticated ? state.auth.user?.email || "Signed in" : "Not signed in"),
      resourceCard("Active study", currentStudy() ? currentStudy().name : "No active study selected"),
      resourceCard("Known studies in browser session", `${state.studies.length}`),
    );
  }

  document.getElementById("clear-study-selection")?.addEventListener("click", () => {
    setActiveStudyId("");
    window.location.reload();
  });
}

async function initSignIn() {
  if (state.auth.authenticated) {
    window.location.assign("/dashboard");
    return;
  }

  const form = document.getElementById("sign-in-form");
  const output = document.getElementById("sign-in-output");
  const signInModeButton = document.getElementById("auth-mode-sign-in");
  const signUpModeButton = document.getElementById("auth-mode-sign-up");
  const authModeLabel = document.getElementById("auth-mode-label");
  const authModeCopy = document.getElementById("auth-mode-copy");
  const submitButton = form?.querySelector('button[type="submit"]');
  const title = document.querySelector(".panel-card--auth h1");
  let authMode = "sign-in";

  function refreshAuthModeUi() {
    if (!submitButton) return;
    submitButton.textContent = authMode === "sign-up" ? "Create account" : "Sign in";
    if (title) {
      title.textContent =
        authMode === "sign-up"
          ? "Create an account to access your research workspace."
          : "Sign in to access your research workspace.";
    }
    if (authModeLabel) {
      authModeLabel.textContent = authMode === "sign-up" ? "Current mode: Create account" : "Current mode: Sign in";
    }
    if (authModeCopy) {
      authModeCopy.textContent =
        authMode === "sign-up"
          ? "Create-account mode is active. Enter your email and password, then click the Create account button below."
          : "Sign-in mode is active. Enter your email and password, then submit the form.";
    }
    signInModeButton?.classList.toggle("is-active", authMode === "sign-in");
    signUpModeButton?.classList.toggle("is-active", authMode === "sign-up");
    signInModeButton?.setAttribute("aria-pressed", authMode === "sign-in" ? "true" : "false");
    signUpModeButton?.setAttribute("aria-pressed", authMode === "sign-up" ? "true" : "false");
  }

  signInModeButton?.addEventListener("click", () => {
    authMode = "sign-in";
    setNodeContent(output, "Enter your credentials to start a session.");
    refreshAuthModeUi();
  });
  signUpModeButton?.addEventListener("click", () => {
    authMode = "sign-up";
    setNodeContent(output, "Create-account mode enabled. Submit the form below to register.");
    refreshAuthModeUi();
  });
  refreshAuthModeUi();

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");
    if (!email || !password) {
      setNodeContent(output, "Email and password are required.");
      return;
    }

    try {
      const endpoint = authMode === "sign-up" ? "/api/auth/sign-up" : "/api/auth/sign-in";
      const result = await callApi(endpoint, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      if (result?.authenticated) {
        setNodeContent(output, result?.message || "Signed in successfully. Redirecting...");
        window.setTimeout(() => window.location.assign("/dashboard"), 250);
        return;
      }

      if (authMode === "sign-up") {
        setNodeContent(
          output,
          result?.message || "Account created. Check your email to confirm, then sign in.",
        );
        authMode = "sign-in";
        refreshAuthModeUi();
        return;
      }

      setNodeContent(output, "Unable to start a session.");
    } catch (error) {
      setNodeContent(output, error.message || "Sign in failed.");
    }
  });
}

async function initPage() {
  try {
    await loadAuthSession();
    if (state.auth.authenticated) {
      await loadStudies();
    } else {
      state.studies = [];
      setActiveStudyId("");
    }

    if (!PUBLIC_PAGES.has(page) && !state.auth.authenticated) {
      window.location.assign("/sign-in");
      return;
    }

    renderHeader();
    renderWorkspaceNav();
    installCardSpotlight();

    switch (page) {
      case "dashboard":
        await initDashboard();
        break;
      case "studies":
        await initStudies();
        break;
      case "workspace":
        await initWorkspace();
        break;
      case "protocol":
        await initProtocols();
        break;
      case "personas":
        await initPersonas();
        break;
      case "interview-guide":
        await initInterviewGuide();
        break;
      case "transcripts":
        await initTranscripts();
        break;
      case "simulations":
        await initSimulations();
        break;
      case "comparisons":
        await initComparisons();
        break;
      case "settings":
        await initSettings();
        break;
      case "sign-in":
        await initSignIn();
        break;
      default:
        break;
    }
  } catch (error) {
    console.error(error);
  } finally {
    bodyReady();
  }
}

installPageTransitions();
initPage();
