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

function renderInitialNavigation() {
  elements.categoryList.replaceChildren();
  elements.commandList.replaceChildren();
  for (const command of state.schema.commands) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "command-card";
    const name = document.createElement("strong");
    name.textContent = command.name;
    const summary = document.createElement("small");
    summary.textContent = command.summary;
    button.append(name, summary);
    elements.commandList.append(button);
  }
}

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
    renderInitialNavigation();
  } catch (error) {
    elements.connection.textContent = "Connection failed";
    elements.connection.title = error.message;
  }
}

boot();
