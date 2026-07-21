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
};

const elements = {
  connection: document.querySelector("#connection-status"),
  stats: document.querySelectorAll("#surface-stats dd"),
  categoryList: document.querySelector("#category-list"),
  commandList: document.querySelector("#command-list"),
  search: document.querySelector("#command-search"),
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
  renderNavigation();
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
  } catch (error) {
    elements.connection.textContent = "Connection failed";
    elements.connection.title = error.message;
  }
}

boot();
