"use strict";

const token = document
  .querySelector('meta[name="flowmpeg-token"]')
  .getAttribute("content");

const state = {
  schema: null,
  selectedCategory: "all",
  selectedCommand: null,
  query: "",
  preview: null,
  favorites: new Set(),
  jobs: new Map(),
  readiness: null,
  pollTimer: null,
  fileBrowser: null,
  lastDirectory: null,
  presets: [],
};

const elements = {
  connection: document.querySelector("#connection-status"),
  stats: document.querySelectorAll("#surface-stats dd"),
  categoryList: document.querySelector("#category-list"),
  commandList: document.querySelector("#command-list"),
  search: document.querySelector("#command-search"),
  welcome: document.querySelector("#welcome-panel"),
  commandPanel: document.querySelector("#command-panel"),
  commandCategory: document.querySelector("#command-category"),
  commandTitle: document.querySelector("#command-title"),
  commandSummary: document.querySelector("#command-summary"),
  commandFacts: document.querySelector("#command-facts"),
  commandPreview: document.querySelector("#command-preview"),
  form: document.querySelector("#command-form"),
  basicFields: document.querySelector("#basic-fields"),
  advancedFields: document.querySelector("#advanced-fields"),
  advancedSection: document.querySelector("#advanced-section"),
  previewButton: document.querySelector("#preview-button"),
  runButton: document.querySelector("#run-button"),
  copyCommand: document.querySelector("#copy-command"),
  formErrors: document.querySelector("#form-errors"),
  themeSelect: document.querySelector("#theme-select"),
  toastRegion: document.querySelector("#toast-region"),
  readinessCard: document.querySelector("#readiness-card"),
  readinessTitle: document.querySelector("#readiness-title"),
  readinessMessage: document.querySelector("#readiness-message"),
  ffmpegStatus: document.querySelector("#ffmpeg-status"),
  ffprobeStatus: document.querySelector("#ffprobe-status"),
  favoriteButton: document.querySelector("#favorite-button"),
  jobList: document.querySelector("#job-list"),
  clearJobs: document.querySelector("#clear-jobs"),
  fileDialog: document.querySelector("#file-dialog"),
  fileDialogTitle: document.querySelector("#file-dialog-title"),
  fileDialogClose: document.querySelector("#file-dialog-close"),
  fileParent: document.querySelector("#file-parent"),
  fileCurrentPath: document.querySelector("#file-current-path"),
  fileGo: document.querySelector("#file-go"),
  fileNewFolder: document.querySelector("#file-new-folder"),
  fileEntries: document.querySelector("#file-entries"),
  fileSelectionSummary: document.querySelector("#file-selection-summary"),
  fileCancel: document.querySelector("#file-cancel"),
  fileUsePath: document.querySelector("#file-use-path"),
  outputNameField: document.querySelector("#output-name-field"),
  outputFileName: document.querySelector("#output-file-name"),
  presetSelect: document.querySelector("#preset-select"),
  savePreset: document.querySelector("#save-preset"),
  deletePreset: document.querySelector("#delete-preset"),
};

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = new Headers(options.headers || {});
  if (method !== "GET") {
    headers.set("Content-Type", "application/json");
    headers.set("X-Flowmpeg-Token", token);
  }
  const response = await fetch(path, {...options, method, headers});
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.message || "The local request failed");
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function visibleCommands() {
  const query = state.query.trim().toLowerCase();
  return state.schema.commands.filter((command) => {
    const matchesCategory =
      state.selectedCategory === "all" ||
      command.category === state.selectedCategory;
    const text = [
      command.name,
      command.summary,
      ...command.aliases,
      ...command.tags,
    ]
      .join(" ")
      .toLowerCase();
    return matchesCategory && (!query || text.includes(query));
  }).sort((first, second) => {
    const favoriteDifference =
      Number(state.favorites.has(second.name)) -
      Number(state.favorites.has(first.name));
    return favoriteDifference || first.name.localeCompare(second.name);
  });
}

function categoryButton(value, label, count) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "category-button";
  button.classList.toggle("selected", state.selectedCategory === value);
  button.setAttribute(
    "aria-pressed",
    String(state.selectedCategory === value),
  );
  button.textContent = `${label} ${count}`;
  button.addEventListener("click", () => {
    state.selectedCategory = value;
    renderNavigation();
  });
  return button;
}

function selectCommand(command) {
  state.selectedCommand = command;
  state.preview = null;
  elements.welcome.hidden = true;
  elements.commandPanel.hidden = false;
  elements.commandCategory.textContent = command.category;
  elements.commandTitle.textContent = command.name
    .split("-")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
  elements.commandSummary.textContent = command.summary;
  elements.commandPreview.textContent =
    "Fill the required fields to preview the command.";
  elements.commandFacts.replaceChildren(
    factElement(`Input: ${command.inputKind}`),
    factElement(`Output: ${command.outputKind}`),
  );
  if (command.aliases.length) {
    elements.commandFacts.append(
      factElement(`Shortcuts: ${command.aliases.join(", ")}`),
    );
  }
  updateFavoriteButton();
  elements.runButton.disabled = command.name === "ui";
  elements.runButton.title =
    command.name === "ui"
      ? "The interface is already running"
      : "Run this command on the current computer";
  renderForm(command);
  renderPresetOptions();
  history.replaceState(null, "", `#command=${encodeURIComponent(command.name)}`);
  renderNavigation();
  elements.commandPanel.scrollIntoView({behavior: "smooth", block: "start"});
}

function loadFavorites() {
  try {
    const values = JSON.parse(localStorage.getItem("flowmpeg-favorites") || "[]");
    if (Array.isArray(values)) {
      state.favorites = new Set(
        values.filter((value) => typeof value === "string"),
      );
    }
  } catch {
    state.favorites = new Set();
  }
}

function loadPresets() {
  try {
    const values = JSON.parse(localStorage.getItem("flowmpeg-presets") || "[]");
    state.presets = Array.isArray(values)
      ? values.filter(
          (value) =>
            value &&
            typeof value.id === "string" &&
            typeof value.name === "string" &&
            typeof value.command === "string" &&
            value.values &&
            typeof value.values === "object",
        )
      : [];
  } catch {
    state.presets = [];
  }
}

function savePresets() {
  localStorage.setItem("flowmpeg-presets", JSON.stringify(state.presets));
}

function renderPresetOptions() {
  elements.presetSelect.replaceChildren(
    new Option("Choose a saved preset", ""),
  );
  if (!state.selectedCommand) {
    return;
  }
  const presets = state.presets
    .filter((preset) => preset.command === state.selectedCommand.name)
    .sort((first, second) => first.name.localeCompare(second.name));
  for (const preset of presets) {
    elements.presetSelect.append(new Option(preset.name, preset.id));
  }
  elements.deletePreset.disabled = true;
}

elements.savePreset.addEventListener("click", () => {
  if (!state.selectedCommand) {
    return;
  }
  const name = window.prompt("Preset name");
  if (!name?.trim()) {
    return;
  }
  state.presets.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    name: name.trim(),
    command: state.selectedCommand.name,
    values: collectValues(),
  });
  savePresets();
  renderPresetOptions();
  showToast("Preset saved in this browser.");
});

elements.presetSelect.addEventListener("change", () => {
  const preset = state.presets.find(
    (value) => value.id === elements.presetSelect.value,
  );
  elements.deletePreset.disabled = !preset;
  if (!preset) {
    return;
  }
  applyFormValues(preset.values);
  showToast("Preset loaded.");
});

elements.deletePreset.addEventListener("click", () => {
  const id = elements.presetSelect.value;
  if (!id) {
    return;
  }
  state.presets = state.presets.filter((preset) => preset.id !== id);
  savePresets();
  renderPresetOptions();
  showToast("Preset deleted.");
});

function applyFormValues(values) {
  for (const field of state.selectedCommand.fields) {
    const control = elements.form.elements.namedItem(field.name);
    if (!control || !(field.name in values)) {
      continue;
    }
    const value = values[field.name];
    const clear = elements.form.querySelector(
      `[data-clear-for="${field.name}"]`,
    );
    if (clear) {
      clear.checked = value === null;
      control.disabled = clear.checked;
    }
    if (field.kind === "boolean") {
      control.checked = Boolean(value);
    } else if (field.multiple && Array.isArray(value)) {
      control.value = value.join("\n");
    } else if (value !== null) {
      control.value = String(value);
    }
  }
  elements.form.dispatchEvent(new Event("input", {bubbles: true}));
}

function updateFavoriteButton() {
  const saved = state.favorites.has(state.selectedCommand?.name);
  elements.favoriteButton.textContent = saved
    ? "Remove favorite"
    : "Save favorite";
  elements.favoriteButton.setAttribute("aria-pressed", String(saved));
}

elements.favoriteButton.addEventListener("click", () => {
  if (!state.selectedCommand) {
    return;
  }
  const name = state.selectedCommand.name;
  if (state.favorites.has(name)) {
    state.favorites.delete(name);
    showToast("Favorite removed.");
  } else {
    state.favorites.add(name);
    showToast("Favorite saved on this computer.");
  }
  localStorage.setItem(
    "flowmpeg-favorites",
    JSON.stringify([...state.favorites].sort()),
  );
  updateFavoriteButton();
  renderNavigation();
});

function renderForm(command) {
  elements.form.reset();
  elements.basicFields.replaceChildren();
  elements.advancedFields.replaceChildren();
  for (const field of command.fields) {
    const control = renderField(field);
    const target = field.advanced
      ? elements.advancedFields
      : elements.basicFields;
    target.append(control);
  }
  elements.advancedSection.hidden = !command.fields.some(
    (field) => field.advanced,
  );
  elements.advancedSection.open = false;
}

function renderField(field) {
  if (field.kind === "boolean") {
    return renderBooleanField(field);
  }
  const wrapper = document.createElement("div");
  wrapper.className = "field";
  wrapper.classList.toggle("wide", field.multiple || field.pathRole !== "none");

  const label = document.createElement("label");
  label.className = "field-label";
  label.htmlFor = `field-${field.name}`;
  label.textContent = field.label;
  if (field.required) {
    const required = document.createElement("span");
    required.className = "required-mark";
    required.textContent = " required";
    label.append(required);
  }

  const control = createFieldControl(field);
  control.id = `field-${field.name}`;
  control.name = field.name;
  control.required = field.required;
  control.setAttribute("aria-describedby", `help-${field.name}`);

  const help = document.createElement("span");
  help.className = "field-help";
  help.id = `help-${field.name}`;
  help.textContent = field.help || pathHelp(field.pathRole);
  wrapper.append(label);
  if (field.pathRole !== "none") {
    const row = document.createElement("div");
    row.className = "path-control";
    const browse = document.createElement("button");
    browse.type = "button";
    browse.className = "secondary-button";
    browse.textContent = "Browse";
    browse.addEventListener("click", () => openFileDialog(field, control));
    row.append(control, browse);
    wrapper.append(row);
  } else {
    wrapper.append(control);
  }
  wrapper.append(help);

  if (field.clearFlags.length) {
    const clearLabel = document.createElement("label");
    clearLabel.className = "clear-field";
    const clear = document.createElement("input");
    clear.type = "checkbox";
    clear.dataset.clearFor = field.name;
    clear.addEventListener("change", () => {
      control.disabled = clear.checked;
    });
    const text = document.createElement("span");
    text.textContent = `Use ${field.clearFlags[0]} instead`;
    clearLabel.append(clear, text);
    wrapper.append(clearLabel);
  }
  return wrapper;
}

function renderBooleanField(field) {
  const label = document.createElement("label");
  label.className = "boolean-field";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = field.name;
  input.checked = Boolean(field.default);
  const text = document.createElement("span");
  const title = document.createElement("strong");
  title.textContent = field.label;
  const help = document.createElement("small");
  help.className = "field-help";
  help.textContent = field.help;
  text.append(title, help);
  label.append(input, text);
  return label;
}

function createFieldControl(field) {
  if (field.multiple) {
    const textarea = document.createElement("textarea");
    textarea.rows = 3;
    textarea.placeholder = "One path per line";
    return textarea;
  }
  if (field.kind === "choice") {
    const select = document.createElement("select");
    if (!field.required && field.default === null) {
      select.append(new Option("Use command default", ""));
    }
    for (const choice of field.choices) {
      const option = new Option(choice, choice);
      option.selected = String(field.default) === choice;
      select.append(option);
    }
    return select;
  }
  const input = document.createElement("input");
  input.type = field.kind === "number" ? "number" : "text";
  if (field.kind === "number") {
    input.step = field.integer ? "1" : "any";
    if (field.minimum !== null) {
      input.min = String(field.minimum);
      input.dataset.exclusiveMinimum = String(field.exclusiveMinimum);
    }
  }
  if (field.default !== null) {
    input.value = String(field.default);
  }
  input.placeholder = pathPlaceholder(field.pathRole);
  return input;
}

function pathPlaceholder(role) {
  const placeholders = {
    "input-file": "Choose or enter an input path",
    "input-files": "Enter one input path per line",
    "input-directory": "Choose an input folder",
    "output-file": "Choose an output path",
    "output-directory": "Choose an output folder",
  };
  return placeholders[role] || "";
}

function pathHelp(role) {
  return role === "none" ? "" : "This path stays on your computer.";
}

async function openFileDialog(field, control) {
  state.fileBrowser = {
    field,
    control,
    listing: null,
    selected: new Set(),
  };
  elements.fileDialogTitle.textContent = field.label;
  elements.outputNameField.hidden = field.pathRole !== "output-file";
  elements.fileNewFolder.hidden = !field.pathRole.startsWith("output-");
  elements.outputFileName.value = "";
  elements.fileSelectionSummary.textContent = "Nothing selected";
  elements.fileDialog.showModal();
  await loadDirectory(state.lastDirectory);
}

async function loadDirectory(path) {
  elements.fileEntries.replaceChildren();
  const loading = document.createElement("p");
  loading.className = "empty-state";
  loading.textContent = "Loading local paths...";
  elements.fileEntries.append(loading);
  try {
    const listing = await api("/api/files", {
      method: "POST",
      body: JSON.stringify({path: path || null}),
    });
    state.fileBrowser.listing = listing;
    state.fileBrowser.selected.clear();
    state.lastDirectory = listing.path;
    elements.fileCurrentPath.value = listing.path;
    elements.fileParent.disabled = !listing.parent;
    renderFileEntries();
  } catch (error) {
    elements.fileEntries.replaceChildren();
    const message = document.createElement("p");
    message.className = "form-errors";
    message.textContent = error.message;
    elements.fileEntries.append(message);
  }
}

function renderFileEntries() {
  const browser = state.fileBrowser;
  elements.fileEntries.replaceChildren();
  if (!browser.listing.entries.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "This folder is empty.";
    elements.fileEntries.append(empty);
  }
  for (const entry of browser.listing.entries) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "file-entry";
    button.classList.toggle("selected", browser.selected.has(entry.path));
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", String(browser.selected.has(entry.path)));
    const name = document.createElement("span");
    name.textContent = entry.name;
    const detail = document.createElement("small");
    detail.textContent = entry.directory ? "Folder" : formatBytes(entry.size);
    button.append(name, detail);
    button.addEventListener("dblclick", () => {
      if (entry.directory) {
        loadDirectory(entry.path);
      }
    });
    button.addEventListener("click", () => toggleFileSelection(entry));
    elements.fileEntries.append(button);
  }
  if (browser.listing.truncated) {
    const warning = document.createElement("p");
    warning.className = "empty-state";
    warning.textContent = "Only the first 1000 entries are shown.";
    elements.fileEntries.append(warning);
  }
}

function toggleFileSelection(entry) {
  const browser = state.fileBrowser;
  const wantsDirectory = ["input-directory", "output-directory"].includes(
    browser.field.pathRole,
  );
  if (entry.directory !== wantsDirectory && browser.field.pathRole !== "input-files") {
    return;
  }
  if (entry.directory && browser.field.pathRole === "input-files") {
    loadDirectory(entry.path);
    return;
  }
  if (browser.field.pathRole === "input-files") {
    if (browser.selected.has(entry.path)) {
      browser.selected.delete(entry.path);
    } else {
      browser.selected.add(entry.path);
    }
  } else {
    browser.selected.clear();
    browser.selected.add(entry.path);
  }
  const count = browser.selected.size;
  elements.fileSelectionSummary.textContent = count
    ? `${count} path${count === 1 ? "" : "s"} selected`
    : "Nothing selected";
  renderFileEntries();
}

function formatBytes(value) {
  if (value === null) {
    return "File";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 ** 2) {
    return `${(value / 1024).toFixed(1)} KiB`;
  }
  if (value < 1024 ** 3) {
    return `${(value / 1024 ** 2).toFixed(1)} MiB`;
  }
  return `${(value / 1024 ** 3).toFixed(1)} GiB`;
}

function closeFileDialog() {
  elements.fileDialog.close();
  state.fileBrowser = null;
}

elements.fileParent.addEventListener("click", () => {
  if (state.fileBrowser?.listing?.parent) {
    loadDirectory(state.fileBrowser.listing.parent);
  }
});
elements.fileGo.addEventListener("click", () => {
  loadDirectory(elements.fileCurrentPath.value.trim());
});
elements.fileNewFolder.addEventListener("click", async () => {
  const name = window.prompt("New folder name");
  if (name === null || !state.fileBrowser?.listing) {
    return;
  }
  try {
    await api("/api/directories", {
      method: "POST",
      body: JSON.stringify({
        parent: state.fileBrowser.listing.path,
        name: name.trim(),
      }),
    });
    showToast("Folder created.");
    await loadDirectory(state.fileBrowser.listing.path);
  } catch (error) {
    showToast(error.message);
  }
});
elements.fileCurrentPath.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadDirectory(elements.fileCurrentPath.value.trim());
  }
});
elements.fileDialogClose.addEventListener("click", closeFileDialog);
elements.fileCancel.addEventListener("click", closeFileDialog);
elements.fileUsePath.addEventListener("click", () => {
  const browser = state.fileBrowser;
  if (!browser?.listing) {
    return;
  }
  let paths = [...browser.selected];
  if (browser.field.pathRole === "output-file") {
    const name = elements.outputFileName.value.trim();
    if (!name || name.includes("/") || name.includes("\\")) {
      showToast("Enter a file name without folder separators.");
      elements.outputFileName.focus();
      return;
    }
    paths = [joinLocalPath(browser.listing.path, name)];
  }
  if (["input-directory", "output-directory"].includes(browser.field.pathRole)) {
    paths = paths.length ? paths : [browser.listing.path];
  }
  if (!paths.length) {
    showToast("Select a path first.");
    return;
  }
  browser.control.value = browser.field.multiple
    ? paths.join("\n")
    : paths[0];
  browser.control.dispatchEvent(new Event("input", {bubbles: true}));
  closeFileDialog();
});

function joinLocalPath(folder, name) {
  const separator = folder.includes("\\") ? "\\" : "/";
  return folder.endsWith(separator) ? `${folder}${name}` : `${folder}${separator}${name}`;
}

function collectValues() {
  const values = {};
  for (const field of state.selectedCommand.fields) {
    const control = elements.form.elements.namedItem(field.name);
    if (!control) {
      continue;
    }
    const clear = elements.form.querySelector(
      `[data-clear-for="${field.name}"]`,
    );
    if (clear?.checked) {
      values[field.name] = null;
      continue;
    }
    if (field.kind === "boolean") {
      values[field.name] = control.checked;
      continue;
    }
    if (field.multiple) {
      const items = control.value
        .split(/\r?\n/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (items.length) {
        values[field.name] = items;
      }
      continue;
    }
    if (control.value === "") {
      continue;
    }
    values[field.name] =
      field.kind === "number" ? Number(control.value) : control.value;
  }
  return values;
}

function clearFormErrors() {
  elements.formErrors.hidden = true;
  elements.formErrors.replaceChildren();
  for (const control of elements.form.elements) {
    control.removeAttribute("aria-invalid");
  }
}

function showFormIssues(issues) {
  clearFormErrors();
  const list = document.createElement("ul");
  for (const issue of issues) {
    const item = document.createElement("li");
    item.textContent = issue.message;
    list.append(item);
    if (issue.field) {
      const control = elements.form.elements.namedItem(issue.field);
      control?.setAttribute("aria-invalid", "true");
    }
  }
  elements.formErrors.append(list);
  elements.formErrors.hidden = false;
}

async function requestPreview() {
  if (!state.selectedCommand) {
    return;
  }
  clearFormErrors();
  elements.previewButton.disabled = true;
  elements.commandPreview.textContent = "Building command preview...";
  try {
    const preview = await api("/api/preview", {
      method: "POST",
      body: JSON.stringify({
        command: state.selectedCommand.name,
        values: collectValues(),
      }),
    });
    state.preview = preview;
    elements.commandPreview.textContent = preview.display;
    elements.copyCommand.disabled = false;
  } catch (error) {
    state.preview = null;
    elements.copyCommand.disabled = true;
    elements.commandPreview.textContent = "The command needs attention.";
    if (error.data?.issues) {
      showFormIssues(error.data.issues);
    } else {
      showFormIssues([{message: error.message, field: null}]);
    }
  } finally {
    elements.previewButton.disabled = false;
  }
}

elements.previewButton.addEventListener("click", requestPreview);
elements.form.addEventListener("input", () => {
  state.preview = null;
  elements.copyCommand.disabled = true;
  clearFormErrors();
});
elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  startJob();
});

async function startJob() {
  if (!state.selectedCommand || elements.runButton.disabled) {
    return;
  }
  const values = collectValues();
  if (!confirmSensitiveJob(state.selectedCommand.name, values)) {
    return;
  }
  clearFormErrors();
  elements.runButton.disabled = true;
  elements.runButton.textContent = "Starting...";
  try {
    const job = await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({
        command: state.selectedCommand.name,
        values,
      }),
    });
    state.jobs.set(job.id, job);
    renderJobs();
    scheduleJobPoll();
    showToast("Local job started.");
  } catch (error) {
    if (error.data?.issues) {
      showFormIssues(error.data.issues);
    } else {
      showFormIssues([{message: error.message, field: null}]);
    }
  } finally {
    elements.runButton.disabled = state.selectedCommand?.name === "ui";
    elements.runButton.textContent = "Run locally";
  }
}

function confirmSensitiveJob(command, values) {
  if (command === "setup" && values.install) {
    return window.confirm(
      "This will run a system package manager on this computer. Continue?",
    );
  }
  if (values.overwrite) {
    return window.confirm(
      "Overwrite is enabled. Existing output at the selected path may be replaced. Continue?",
    );
  }
  return true;
}

function renderJobs() {
  elements.jobList.replaceChildren();
  const jobs = [...state.jobs.values()].sort(
    (first, second) => second.createdAt - first.createdAt,
  );
  if (!jobs.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No jobs in this session.";
    elements.jobList.append(empty);
    elements.clearJobs.disabled = true;
    return;
  }
  elements.clearJobs.disabled = !jobs.some((job) =>
    ["succeeded", "failed", "cancelled"].includes(job.status),
  );
  for (const job of jobs) {
    const card = document.createElement("article");
    card.className = "job-card";
    card.dataset.status = job.status;
    const header = document.createElement("header");
    const status = document.createElement("span");
    status.className = "job-status";
    status.textContent = job.status;
    const command = document.createElement("code");
    command.textContent = job.display;
    header.append(status, command);
    card.append(header);
    const timing = document.createElement("p");
    timing.className = "job-timing";
    timing.textContent = jobTiming(job);
    card.append(timing);
    if (job.output) {
      const output = document.createElement("pre");
      output.className = "job-output";
      output.textContent = job.output;
      output.tabIndex = 0;
      card.append(output);
    }
    if (["queued", "running"].includes(job.status)) {
      const actions = document.createElement("div");
      actions.className = "job-actions";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "quiet-button";
      cancel.textContent = "Cancel job";
      cancel.addEventListener("click", () => cancelJob(job.id, cancel));
      actions.append(cancel);
      card.append(actions);
    }
    elements.jobList.append(card);
  }
}

async function cancelJob(jobId, button) {
  button.disabled = true;
  button.textContent = "Cancelling...";
  try {
    const job = await api(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: "POST",
    });
    state.jobs.set(job.id, job);
    renderJobs();
    scheduleJobPoll();
  } catch (error) {
    showToast(error.message);
    button.disabled = false;
    button.textContent = "Cancel job";
  }
}

elements.clearJobs.addEventListener("click", async () => {
  elements.clearJobs.disabled = true;
  try {
    const result = await api("/api/jobs/clear", {method: "POST"});
    for (const [jobId, job] of state.jobs) {
      if (["succeeded", "failed", "cancelled"].includes(job.status)) {
        state.jobs.delete(jobId);
      }
    }
    renderJobs();
    showToast(`${result.cleared} finished job records cleared.`);
  } catch (error) {
    showToast(error.message);
    renderJobs();
  }
});

function jobTiming(job) {
  const started = job.startedAt || job.createdAt;
  const ended = job.finishedAt || Date.now() / 1000;
  const seconds = Math.max(0, ended - started);
  const duration = seconds < 60
    ? `${seconds.toFixed(1)} seconds`
    : `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return job.finishedAt ? `Finished in ${duration}` : `Elapsed ${duration}`;
}

function scheduleJobPoll() {
  window.clearTimeout(state.pollTimer);
  const active = [...state.jobs.values()].some((job) =>
    ["queued", "running"].includes(job.status),
  );
  if (active) {
    state.pollTimer = window.setTimeout(loadJobs, 750);
  }
}

async function loadJobs() {
  try {
    const data = await api("/api/jobs");
    for (const job of data.jobs) {
      const previous = state.jobs.get(job.id);
      state.jobs.set(job.id, job);
      if (
        previous &&
        previous.status !== job.status &&
        ["succeeded", "failed", "cancelled"].includes(job.status)
      ) {
        showToast(`Job ${job.status}.`);
      }
    }
    renderJobs();
  } catch (error) {
    showToast(error.message);
  } finally {
    scheduleJobPoll();
  }
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), 3500);
}

elements.copyCommand.addEventListener("click", async () => {
  if (!state.preview) {
    return;
  }
  try {
    await navigator.clipboard.writeText(state.preview.display);
    showToast("Command copied to the clipboard.");
  } catch {
    showToast("The browser could not copy the command.");
  }
});

function applyTheme(theme) {
  if (theme === "system") {
    document.documentElement.removeAttribute("data-theme");
  } else {
    document.documentElement.dataset.theme = theme;
  }
}

const savedTheme = localStorage.getItem("flowmpeg-theme");
if (["system", "light", "dark"].includes(savedTheme)) {
  elements.themeSelect.value = savedTheme;
}
applyTheme(elements.themeSelect.value);
elements.themeSelect.addEventListener("change", () => {
  const theme = elements.themeSelect.value;
  localStorage.setItem("flowmpeg-theme", theme);
  applyTheme(theme);
});

document.addEventListener("keydown", (event) => {
  const editing = ["INPUT", "TEXTAREA", "SELECT"].includes(
    document.activeElement?.tagName,
  );
  if (event.key === "/" && !editing) {
    event.preventDefault();
    elements.search.focus();
    return;
  }
  if (event.key === "Escape" && document.activeElement === elements.search) {
    elements.search.value = "";
    state.query = "";
    renderNavigation();
    return;
  }
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    if (!elements.runButton.disabled) {
      elements.form.requestSubmit();
    } else {
      requestPreview();
    }
  }
});

elements.commandList.addEventListener("keydown", (event) => {
  if (!['ArrowDown', 'ArrowUp'].includes(event.key)) {
    return;
  }
  const buttons = [...elements.commandList.querySelectorAll(".command-card")];
  const current = buttons.indexOf(document.activeElement);
  if (current < 0) {
    return;
  }
  event.preventDefault();
  const direction = event.key === "ArrowDown" ? 1 : -1;
  const next = (current + direction + buttons.length) % buttons.length;
  buttons[next].focus();
});

function factElement(text) {
  const fact = document.createElement("span");
  fact.className = "fact";
  fact.textContent = text;
  return fact;
}

function renderNavigation() {
  elements.categoryList.replaceChildren();
  elements.commandList.replaceChildren();
  elements.categoryList.append(
    categoryButton("all", "All", state.schema.commands.length),
  );
  for (const category of state.schema.categories) {
    const count = state.schema.commands.filter(
      (command) => command.category === category,
    ).length;
    const label = category[0].toUpperCase() + category.slice(1);
    elements.categoryList.append(categoryButton(category, label, count));
  }

  const commands = visibleCommands();
  if (!commands.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No commands match this search.";
    elements.commandList.append(empty);
    return;
  }
  for (const command of commands) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "command-card";
    button.classList.toggle(
      "selected",
      state.selectedCommand?.name === command.name,
    );
    button.setAttribute(
      "aria-pressed",
      String(state.selectedCommand?.name === command.name),
    );
    const name = document.createElement("strong");
    name.textContent = command.name;
    const summary = document.createElement("small");
    summary.textContent = command.summary;
    button.append(name, summary);
    button.addEventListener("click", () => selectCommand(command));
    elements.commandList.append(button);
  }
}

elements.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderNavigation();
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => {
    const command = state.schema?.commands.find(
      (item) => item.name === button.dataset.command,
    );
    if (!command) {
      showToast("This command is not available in the installed version.");
      return;
    }
    selectCommand(command);
  });
});

function toolStatusText(tool) {
  if (tool.ready) {
    return `${tool.name}: ready`;
  }
  return `${tool.name}: ${tool.state.replace("-", " ")}`;
}

function updateToolPill(element, tool) {
  element.textContent = toolStatusText(tool);
  element.classList.toggle("ready", Boolean(tool.ready));
  element.classList.toggle("attention", !tool.ready);
  element.title = [tool.version, tool.path, tool.reason]
    .filter(Boolean)
    .join("\n");
}

function renderReadiness(readiness) {
  state.readiness = readiness;
  elements.readinessCard.classList.toggle("ready", readiness.ready);
  elements.readinessCard.classList.toggle("attention", !readiness.ready);
  updateToolPill(elements.ffmpegStatus, readiness.ffmpeg);
  updateToolPill(elements.ffprobeStatus, readiness.ffprobe);
  if (readiness.ready) {
    elements.readinessTitle.textContent = "Ready for local media work";
    elements.readinessMessage.textContent =
      "Flowmpeg found FFmpeg and FFprobe. Commands can run from this browser.";
    return;
  }
  const missing = [readiness.ffmpeg, readiness.ffprobe]
    .filter((tool) => tool.state === "missing")
    .map((tool) => tool.name)
    .join(" and ");
  if (missing) {
    elements.readinessTitle.textContent = "Setup needed";
    elements.readinessMessage.textContent =
      `${missing} not found. Open setup options or run flowmpeg setup.`;
    return;
  }
  elements.readinessTitle.textContent = "Tool check needs attention";
  elements.readinessMessage.textContent =
    "Flowmpeg found the tools, but one version check did not finish cleanly.";
}

async function boot() {
  try {
    loadFavorites();
    loadPresets();
    const [health, schema, readiness] = await Promise.all([
      api("/api/health"),
      api("/api/schema"),
      api("/api/readiness"),
    ]);
    state.schema = schema;
    elements.connection.textContent = `Ready, version ${health.version}`;
    elements.connection.classList.add("ready");
    elements.stats[0].textContent = String(schema.commands.length);
    elements.stats[1].textContent = String(schema.categories.length);
    elements.stats[2].textContent = readiness.ready ? "Ready" : "Setup";
    renderReadiness(readiness);
    renderNavigation();
    const selectedName = new URLSearchParams(location.hash.slice(1)).get(
      "command",
    );
    const selected = schema.commands.find(
      (command) =>
        command.name === selectedName || command.aliases.includes(selectedName),
    );
    if (selected) {
      selectCommand(selected);
    }
    await loadJobs();
  } catch (error) {
    elements.connection.textContent = "Connection failed";
    elements.connection.title = error.message;
  }
}

boot();
