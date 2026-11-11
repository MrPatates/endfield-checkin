"use strict";

const I18N = {
  en: {
    nextCheck: "Next check",
    runAll: "Check all now",
    running: "Checking…",
    addTitle: "Connect a SKPORT account",
    addIntro: "The bot checks the SKPORT sign-in page regularly and claims the daily reward of every Endfield character bound to the account.",
    methodToken: "Account token (recommended)",
    methodPassword: "Email + password",
    name: "Display name",
    namePlaceholder: "e.g. Main account",
    tokenPlaceholder: "Paste the ACCOUNT_TOKEN cookie value",
    tokenHelpTitle: "How do I get my ACCOUNT_TOKEN?",
    tokenHelp: [
      "Open the SKPORT sign-in page above in your browser and log in to your account.",
      "Press F12 to open the developer tools.",
      "Chrome / Edge: “Application” tab → Cookies. Firefox: “Storage” tab → Cookies.",
      "Select https://game.skport.com and copy the value of the ACCOUNT_TOKEN cookie.",
      "Paste it here. Never share it: it gives access to your account. If you cannot find it, use the email method.",
    ],
    email: "Email",
    password: "Password",
    remember: "Remember the email and password to log in again automatically when the session expires (stored in /config on your server)",
    passwordNote: "Only the session token is kept unless you tick the box above. Accounts created through Google, Apple, etc. have no password: use the token method.",
    advanced: "Advanced options",
    roleOverride: "Character (sk-game-role)",
    roleOverrideHelp: "Leave empty: characters are detected automatically. Only fill it in if detection fails.",
    connect: "Connect account",
    connecting: "Checking the account…",
    added: "Account connected. First check running…",
    settingsTitle: "Settings",
    settingsHint: "These values are set in the container template (Unraid: Docker → Edit).",
    historyTitle: "History",
    noHistory: "Nothing yet.",
    noAccounts: "No account connected yet. Use the form below to connect your SKPORT account.",
    disclaimer: "Community project, not affiliated with GRYPHLINE, Hypergryph or SKPORT. Use at your own risk.",
    sourceEnv: "from template",
    sourceWeb: "added here",
    token: "token",
    autoRelogin: "auto re-login",
    runOne: "Claim now",
    remove: "Remove",
    removeConfirm: "Remove the account “{name}”? Its token will be deleted from the server.",
    envNoRemove: "Defined by the ACCOUNT_TOKEN variable: remove it from the container template.",
    lastCheck: "Last check: {t}",
    lastClaim: "Last claim: {t}",
    never: "never",
    status: {
      ok: "Today's reward claimed ✓",
      waiting: "Not claimed yet",
      error: "Error, retrying soon",
      action_required: "Action required",
      pending: "Waiting for first check",
    },
    level: "Lv. {n}",
    progress: "Check-ins this month: {done} / {total}",
    bonus: "Extra bonus (first 3 check-ins)",
    day: "Day {n}",
    lastRewards: "Last rewards: {r}",
    kinds: {
      network: "Cannot reach SKPORT (network).",
      api_error: "Unexpected SKPORT answer.",
      session_expired: "SKPORT session rejected.",
      token_rejected: "The account token is invalid or expired: connect the account again.",
      login_failed: "Login refused: check the email and password.",
      no_role: "No Endfield character is bound to this SKPORT account.",
      internal: "Internal error, see the container logs.",
      missing_fields: "Enter the email and the password.",
      missing_token: "Paste the ACCOUNT_TOKEN value.",
      invalid_role: "Invalid character format (expected 3_<uid>_<server>).",
      duplicate: "This account is already connected.",
      env_account: "This account comes from the container template.",
      not_found: "Account not found.",
      bad_csrf: "Session expired, reload the page.",
    },
    events: {
      claimed: "Claimed",
      error: "Error",
      action_required: "Action required",
      recovered: "Working again",
      added: "Account connected",
      removed: "Account removed",
    },
    settings: {
      interval: "Check interval",
      retry: "Retry after an error",
      language: "Reward language",
      notify: "Discord notifications",
      password: "Web UI password",
      timezone: "Time zone",
    },
    minutes: "{n} min",
    notify: { all: "claims and errors", errors: "errors only", none: "off" },
    yes: "yes",
    no: "no",
    inTime: "in {d}",
    now: "now",
  },
  fr: {
    nextCheck: "Prochaine vérification",
    runAll: "Tout vérifier maintenant",
    running: "Vérification…",
    addTitle: "Connecter un compte SKPORT",
    addIntro: "Le bot consulte régulièrement la page de connexion SKPORT et récupère la récompense quotidienne de chaque personnage Endfield lié au compte.",
    methodToken: "Jeton de compte (recommandé)",
    methodPassword: "E-mail + mot de passe",
    name: "Nom affiché",
    namePlaceholder: "ex. Compte principal",
    tokenPlaceholder: "Colle la valeur du cookie ACCOUNT_TOKEN",
    tokenHelpTitle: "Comment récupérer mon ACCOUNT_TOKEN ?",
    tokenHelp: [
      "Ouvre la page de connexion SKPORT ci-dessus dans ton navigateur et connecte-toi à ton compte.",
      "Appuie sur F12 pour ouvrir les outils de développement.",
      "Chrome / Edge : onglet « Application » → Cookies. Firefox : onglet « Stockage » → Cookies.",
      "Sélectionne https://game.skport.com et copie la valeur du cookie ACCOUNT_TOKEN.",
      "Colle-la ici. Ne la partage jamais : elle donne accès à ton compte. Si tu ne la trouves pas, utilise la méthode e-mail.",
    ],
    email: "E-mail",
    password: "Mot de passe",
    remember: "Mémoriser l'e-mail et le mot de passe pour se reconnecter automatiquement quand la session expire (stockés dans /config sur ton serveur)",
    passwordNote: "Seul le jeton de session est conservé, sauf si tu coches la case ci-dessus. Les comptes créés via Google, Apple, etc. n'ont pas de mot de passe : utilise la méthode du jeton.",
    advanced: "Options avancées",
    roleOverride: "Personnage (sk-game-role)",
    roleOverrideHelp: "Laisse vide : les personnages sont détectés automatiquement. À remplir seulement si la détection échoue.",
    connect: "Connecter le compte",
    connecting: "Vérification du compte…",
    added: "Compte connecté. Première vérification en cours…",
    settingsTitle: "Réglages",
    settingsHint: "Ces valeurs se modifient dans le template du conteneur (Unraid : Docker → Edit).",
    historyTitle: "Historique",
    noHistory: "Rien pour l'instant.",
    noAccounts: "Aucun compte connecté. Utilise le formulaire ci-dessous pour connecter ton compte SKPORT.",
    disclaimer: "Projet communautaire, non affilié à GRYPHLINE, Hypergryph ou SKPORT. Utilisation à tes risques.",
    sourceEnv: "via le template",
    sourceWeb: "ajouté ici",
    token: "jeton",
    autoRelogin: "reconnexion auto",
    runOne: "Récupérer maintenant",
    remove: "Supprimer",
    removeConfirm: "Supprimer le compte « {name} » ? Son jeton sera effacé du serveur.",
    envNoRemove: "Défini par la variable ACCOUNT_TOKEN : retire-le du template du conteneur.",
    lastCheck: "Dernière vérification : {t}",
    lastClaim: "Dernière récupération : {t}",
    never: "jamais",
    status: {
      ok: "Récompense du jour récupérée ✓",
      waiting: "Pas encore récupérée",
      error: "Erreur, nouvel essai bientôt",
      action_required: "Action requise",
      pending: "En attente de la première vérification",
    },
    level: "Niv. {n}",
    progress: "Connexions ce mois-ci : {done} / {total}",
    bonus: "Bonus (trois premières connexions)",
    day: "Jour {n}",
    lastRewards: "Dernières récompenses : {r}",
    kinds: {
      network: "SKPORT est injoignable (réseau).",
      api_error: "Réponse inattendue de SKPORT.",
      session_expired: "Session SKPORT refusée.",
      token_rejected: "Le jeton du compte est invalide ou expiré : reconnecte le compte.",
      login_failed: "Connexion refusée : vérifie l'e-mail et le mot de passe.",
      no_role: "Aucun personnage Endfield n'est lié à ce compte SKPORT.",
      internal: "Erreur interne, consulte les logs du conteneur.",
      missing_fields: "Saisis l'e-mail et le mot de passe.",
      missing_token: "Colle la valeur de l'ACCOUNT_TOKEN.",
      invalid_role: "Format de personnage invalide (attendu : 3_<uid>_<serveur>).",
      duplicate: "Ce compte est déjà connecté.",
      env_account: "Ce compte provient du template du conteneur.",
      not_found: "Compte introuvable.",
      bad_csrf: "Session expirée, recharge la page.",
    },
    events: {
      claimed: "Récupéré",
      error: "Erreur",
      action_required: "Action requise",
      recovered: "Fonctionne de nouveau",
      added: "Compte connecté",
      removed: "Compte supprimé",
    },
    settings: {
      interval: "Intervalle de vérification",
      retry: "Nouvel essai après erreur",
      language: "Langue des récompenses",
      notify: "Notifications Discord",
      password: "Mot de passe de l'interface",
      timezone: "Fuseau horaire",
    },
    minutes: "{n} min",
    notify: { all: "récupérations et erreurs", errors: "erreurs seulement", none: "désactivées" },
    yes: "oui",
    no: "non",
    inTime: "dans {d}",
    now: "maintenant",
  },
};

const LANG = (navigator.language || "en").toLowerCase().startsWith("fr") ? "fr" : "en";
const T = I18N[LANG];
const $ = (selector, root = document) => root.querySelector(selector);
let state = null;
let method = "token";
let fastPollUntil = 0;
let pollTimer = null;

function fmt(text, values = {}) {
  return text.replace(/\{(\w+)\}/g, (_, key) => (key in values ? values[key] : ""));
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function formatTime(ts) {
  if (!ts) return T.never;
  return new Intl.DateTimeFormat(LANG, { dateStyle: "short", timeStyle: "short" }).format(new Date(ts * 1000));
}

function formatDelay(seconds) {
  if (seconds <= 30) return T.now;
  const minutes = Math.round(seconds / 60);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return fmt(T.inTime, { d: h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min` });
}

function errorText(kind, detail) {
  return T.kinds[kind] || detail || kind || "?";
}

function applyStaticTranslations() {
  document.documentElement.lang = LANG;
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
  const meta = [account.source === "env" ? T.sourceEnv : T.sourceWeb, `${T.token} ${account.token_hint}`];
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
    showBanner("");
    render();
  } catch (error) {
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
  const body = { method, name: data.get("name"), role: data.get("role") };
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
  applyStaticTranslations();
  document.querySelectorAll("[role=tab]").forEach((tab) => tab.addEventListener("click", () => setMethod(tab.dataset.method)));
  $("#add-form").addEventListener("submit", submitAccount);
  $("#run-all").addEventListener("click", () => runNow(null));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  refresh();
});
