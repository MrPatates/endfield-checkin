"use strict";

let T = {};
let LOCALE = "en-US";
let languages = {};
let languageCode = null;
let languageSetting = null;

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-cache", credentials: "same-origin" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

/* setting: "auto" (browser languages) or an Unraid locale code such as "fr_FR". */
async function loadLanguage(setting) {
  if (!Object.keys(languages).length) languages = await fetchJson("/static/lang/languages.json");
  const supported = Object.keys(languages);
  const browser = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language];
  const code = setting && setting !== "auto" && languages[setting] ? setting : EndfieldI18n.resolveLanguage(browser, supported);
  languageSetting = setting || "auto";
  if (code === languageCode) return;
  const master = await fetchJson("/static/lang/en_US.json");
  let catalog = {};
  if (code !== "en_US") {
    try { catalog = await fetchJson(`/static/lang/${code}.json`); } catch (_) { /* English fallback */ }
  }
  T = EndfieldI18n.mergeCatalog(master, catalog);
  if (languages[code].dir === "rtl") T = EndfieldI18n.isolateLatin(T);
  languageCode = code;
  LOCALE = languages[code].bcp47;
  document.documentElement.lang = LOCALE;
  document.documentElement.dir = languages[code].dir === "rtl" ? "rtl" : "ltr";
  applyStaticTranslations();
}

function languageLabel() {
  const name = (languages[languageCode] || {}).name || languageCode;
  return languageSetting === "auto" ? fmt(T.uiLanguageAuto, { lang: name }) : name;
}
const $ = (selector, root = document) => root.querySelector(selector);
let state = null;
let method = "token";
let fastPollUntil = 0;
let pollTimer = null;

function fmt(text, values = {}) {
  return text.replace(/\{(\w+)\}/g, (_, key) => (key in values ? values[key] : ""));
}

/* Keeps Latin values such as "1 h 05" or "…ZW4=" in order inside right-to-left text. */
function bidi(text) {
  return document.documentElement.dir === "rtl" ? `\u2068${text}\u2069` : text;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function formatTime(ts) {
  if (!ts) return T.never;
  return new Intl.DateTimeFormat(LOCALE, { dateStyle: "short", timeStyle: "short" }).format(new Date(ts * 1000));
}

function formatDelay(seconds) {
  if (seconds <= 30) return T.now;
  const minutes = Math.round(seconds / 60);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return fmt(T.inTime, { d: bidi(h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min`) });
}

function errorText(kind, detail) {
  return (T.kinds || {})[kind] || detail || kind || "?";
}

function applyStaticTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = T[node.dataset.i18n]; });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => { node.placeholder = T[node.dataset.i18nPlaceholder]; });
  document.querySelectorAll("[data-i18n-list]").forEach((node) => {
    node.replaceChildren(...T[node.dataset.i18nList].map((item) => el("li", null, item)));
  });
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": state ? state.csrf : "" },
    body: JSON.stringify(body),
  };
  const response = await fetch(path, { cache: "no-store", credentials: "same-origin", ...options });
  let payload = {};
  try { payload = await response.json(); } catch (_) { /* empty body */ }
  if (!response.ok) {
    const error = new Error(errorText(payload.error, payload.detail));
    error.payload = payload;
    throw error;
  }
  return payload;
}

/* ----------------------------------------------------------------- render */

function accountStatus(account) {
  const s = account.state || {};
  if (!s.status) return "pending";
  if (s.status === "error" || s.status === "action_required") return s.status;
  const roles = s.roles || [];
  return roles.length && roles.every((r) => r.has_today) ? "ok" : "waiting";
}

function tile(item, index, resources, extraClass) {
  const info = resources[item.id] || {};
  const node = el("div", `tile ${extraClass || ""}`);
  if (item.done) node.classList.add("done");
  if (item.available) node.classList.add("available");
  const label = info.name ? `${info.name}${info.count ? " x" + info.count : ""}` : item.id;
  node.title = label;
  node.setAttribute("role", "img");
  node.setAttribute("aria-label", `${fmt(T.day, { n: index + 1 })}: ${label}${item.done ? " ✓" : ""}`);
  if (info.icon) {
    const img = el("img");
    img.alt = "";
    img.referrerPolicy = "no-referrer";
    img.addEventListener("error", () => img.replaceWith(el("span", "tile-placeholder", "?")), { once: true });
    img.src = info.icon;
    node.append(img);
  } else {
    node.append(el("span", "tile-placeholder", "?"));
  }
  node.append(el("span", "tile-count", info.count != null ? String(info.count) : ""));
  node.append(el("span", "tile-day", fmt(T.day, { n: index + 1 })));
  if (item.done) node.append(el("span", "tile-check", "✓"));
  return node;
}

function renderRole(role, resources) {
  const wrap = el("div", "role");
  const head = el("div", "role-head");
  head.append(el("strong", null, role.nickname || role.key));
  if (role.server && role.server !== role.nickname) head.append(el("span", "chip", role.server));
  if (role.level) head.append(el("span", "chip", fmt(T.level, { n: role.level })));
  head.append(el("span", "progress", fmt(T.progress, { done: role.done, total: role.total })));
  wrap.append(head);

  const nextIndex = role.calendar.findIndex((item) => !item.done);
  if (role.first && role.first.length && role.first.some((item) => !item.done)) {
    wrap.append(el("div", "muted small", T.bonus));
    const bonus = el("div", "calendar bonus");
    role.first.forEach((item, i) => bonus.append(tile(item, i, resources)));
    wrap.append(bonus);
  }
  if (role.calendar.length) {
    const grid = el("div", "calendar");
    role.calendar.forEach((item, i) => grid.append(tile(item, i, resources, i === nextIndex ? "next" : "")));
    wrap.append(grid);
  }
  return wrap;
}

function renderAccount(account) {
  const node = $("#account-template").content.firstElementChild.cloneNode(true);
  const s = account.state || {};
  const status = accountStatus(account);
  $(".account-name", node).textContent = account.name;
  const meta = [account.source === "env" ? T.sourceEnv : T.sourceWeb, `${T.token} ${bidi(account.token_hint)}`];
  if (account.auto_relogin) meta.push(T.autoRelogin);
  $(".account-meta", node).textContent = meta.join(" · ");
  const badge = $(".status", node);
  badge.textContent = T.status[status];
  badge.classList.add(`status-${status}`);

  const message = $(".account-message", node);
  if (status === "error" || status === "action_required") {
    message.textContent = errorText(s.kind, s.message);
    if (s.message && T.kinds[s.kind]) message.append(el("span", "muted small detail", s.message));
  } else if (s.last_rewards && s.last_rewards.length) {
    const text = s.last_rewards.map((entry) => entry.rewards.map((r) => (r.count ? `${r.name} x${r.count}` : r.name)).join(", ")).filter(Boolean).join(" · ");
    message.textContent = text ? fmt(T.lastRewards, { r: text }) : "";
  }
  if (!message.textContent) message.remove();

  $(".account-times", node).textContent = [fmt(T.lastCheck, { t: formatTime(s.last_check) }), fmt(T.lastClaim, { t: formatTime(s.last_claim) })].join(" · ");
  const roles = $(".roles", node);
  (s.roles || []).forEach((role) => roles.append(renderRole(role, s.resources || {})));

  const run = $('[data-action="run"]', node);
  run.textContent = state.running ? T.running : T.runOne;
  run.disabled = state.running;
  run.addEventListener("click", () => runNow(account.id));
  const del = $('[data-action="delete"]', node);
  del.textContent = T.remove;
  if (account.source === "env") {
    del.disabled = true;
    del.title = T.envNoRemove;
  } else {
    del.addEventListener("click", () => removeAccount(account));
  }
  return node;
}

function renderSettings() {
  const s = state.settings;
  const rows = [
    [T.settings.interval, fmt(T.minutes, { n: s.check_interval })],
    [T.settings.retry, fmt(T.minutes, { n: s.retry_interval })],
    [T.settings.language, s.language],
    [T.settings.notify, T.notify[s.notify] || s.notify],
    [T.settings.password, s.password_protected ? T.yes : T.no],
    [T.settings.timezone, state.timezone || "UTC"],
    [T.settings.uiLanguage, languageLabel()],
  ];
  $("#settings").replaceChildren(...rows.flatMap(([k, v]) => [el("dt", null, k), el("dd", null, v)]));
}

function renderHistory() {
  const list = $("#history");
  if (!state.history.length) {
    list.replaceChildren(el("li", "muted", T.noHistory));
    return;
  }
  list.replaceChildren(...state.history.map((event) => {
    const item = el("li", `event event-${event.code}`);
    item.append(el("time", "muted small", formatTime(event.ts)));
    const text = el("span", null, `${T.events[event.code] || event.code} — ${event.account}`);
    item.append(text);
    if (event.detail) item.append(el("span", "muted small detail", event.detail));
    return item;
  }));
}

function render() {
  $("#version").textContent = `v${state.version}`;
  const next = state.running ? T.running : state.next_run ? `${formatTime(state.next_run)} (${formatDelay(state.next_run - state.now)})` : "—";
  $("#next-run").textContent = next;
  const runAll = $("#run-all");
  runAll.disabled = state.running || !state.accounts.length;
  runAll.textContent = state.running ? T.running : T.runAll;

  const container = $("#accounts");
  if (!state.accounts.length) {
    container.replaceChildren(el("p", "card empty", T.noAccounts));
  } else {
    container.replaceChildren(...state.accounts.map(renderAccount));
  }
  renderSettings();
  renderHistory();
}

/* ---------------------------------------------------------------- actions */

function showBanner(text, kind = "error") {
  const banner = $("#banner");
  banner.textContent = text;
  banner.className = `banner banner-${kind}`;
  banner.hidden = !text;
}

async function refresh() {
  try {
    state = await api("/api/state");
    await loadLanguage(state.settings.ui_language);
    showBanner("");
    render();
  } catch (error) {
    if (!languageCode) await loadLanguage("auto").catch(() => {});
    showBanner(error.message);
  }
  schedulePoll();
}

function schedulePoll() {
  clearTimeout(pollTimer);
  const fast = (state && state.running) || Date.now() < fastPollUntil;
  pollTimer = setTimeout(refresh, fast ? 2000 : 20000);
}

async function runNow(accountId) {
  try {
    await api("/api/run", accountId ? { account_id: accountId } : {});
    fastPollUntil = Date.now() + 60000;
    setTimeout(refresh, 800);
  } catch (error) {
    showBanner(error.message);
  }
}

async function removeAccount(account) {
  if (!confirm(fmt(T.removeConfirm, { name: account.name }))) return;
  try {
    await api(`/api/accounts/${encodeURIComponent(account.id)}/delete`, {});
    refresh();
  } catch (error) {
    showBanner(error.message);
  }
}

function setMethod(next) {
  method = next;
  document.querySelectorAll("[role=tab]").forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.method === method)));
  document.querySelectorAll("[data-panel]").forEach((panel) => { panel.hidden = panel.dataset.panel !== method; });
}

async function submitAccount(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = $("#add-status");
  const button = $("button[type=submit]", form);
  const data = new FormData(form);
  const body = { method, role: data.get("role") };
  if (method === "token") body.token = data.get("token");
  else Object.assign(body, { email: data.get("email"), password: data.get("password"), remember: data.get("remember") === "on" });
  button.disabled = true;
  status.className = "form-status";
  status.textContent = T.connecting;
  try {
    await api("/api/accounts", body);
    form.reset();
    status.className = "form-status ok";
    status.textContent = T.added;
    fastPollUntil = Date.now() + 60000;
    refresh();
  } catch (error) {
    status.className = "form-status error";
    status.textContent = error.message;
    const detail = error.payload && error.payload.detail;
    if (detail && T.kinds[error.payload.error]) status.append(el("span", "muted small detail", detail));
  } finally {
    button.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[role=tab]").forEach((tab) => tab.addEventListener("click", () => setMethod(tab.dataset.method)));
  $("#add-form").addEventListener("submit", submitAccount);
  $("#run-all").addEventListener("click", () => runNow(null));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  refresh();
});
