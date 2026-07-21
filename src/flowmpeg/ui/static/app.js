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
  favoriteButton: document.querySelector("#favorite-button"),
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
  renderForm(command);
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
  const wrapper = document.createElement("label");
  wrapper.className = "field";
  wrapper.classList.toggle("wide", field.multiple || field.pathRole !== "none");
  wrapper.htmlFor = `field-${field.name}`;

  const label = document.createElement("span");
  label.className = "field-label";
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
  wrapper.append(label, control, help);

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
});

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

async function boot() {
  try {
    loadFavorites();
    const [health, schema] = await Promise.all([
      api("/api/health"),
      api("/api/schema"),
    ]);
    state.schema = schema;
    elements.connection.textContent = `Ready, version ${health.version}`;
    elements.connection.classList.add("ready");
    elements.stats[0].textContent = String(schema.commands.length);
    elements.stats[1].textContent = String(schema.categories.length);
    elements.stats[2].textContent = "Loopback only";
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
  } catch (error) {
    elements.connection.textContent = "Connection failed";
    elements.connection.title = error.message;
  }
}

boot();
