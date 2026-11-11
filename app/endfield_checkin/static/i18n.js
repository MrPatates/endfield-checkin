"use strict";
/* Language selection and catalog merging, shared by the page and the Node tests. */
(function (root) {
  // Language bases whose Unraid locale code is not simply "<base>_<REGION>".
  const ALIASES = {
    ar: "ar_AR", bn: "bn_BN", ca: "ca_CA", cs: "cs_CZ", da: "da_DA", de: "de_DE", el: "el_GR",
    en: "en_US", es: "es_ES", fr: "fr_FR", hr: "hr_HR", hu: "hu_HU", it: "it_IT", ja: "ja_JA",
    ko: "ko_KO", lv: "lv_LV", nb: "no_NO", nl: "nl_NL", nn: "no_NO", no: "no_NO", pl: "pl_PL",
    pt: "pt_PT", ro: "ro_RO", ru: "ru_RU", sv: "sv_SE", uk: "uk_UA", zh: "zh_CN",
  };

  /** Pick the first supported Unraid locale for a list of browser language tags. */
  function resolveLanguage(preferences, supported) {
    const available = new Set(supported);
    for (const raw of preferences || []) {
      if (!raw) continue;
      const tag = String(raw).trim().replace(/_/g, "-");
      const parts = tag.split("-");
      const base = parts[0].toLowerCase();
      if (base === "zh") {
        const traditional = /-(hant|tw|hk|mo)(-|$)/i.test(tag);
        const code = traditional ? "zh_TW" : "zh_CN";
        if (available.has(code)) return code;
        continue;
      }
      if (parts[1]) {
        const exact = `${base}_${parts[1].toUpperCase()}`;
        if (available.has(exact)) return exact;
      }
      if (ALIASES[base] && available.has(ALIASES[base])) return ALIASES[base];
    }
    return "en_US";
  }

  /** Deep-merge a translation over the English master; anything missing or malformed stays English. */
  function mergeCatalog(master, catalog) {
    if (Array.isArray(master)) {
      const ok = Array.isArray(catalog) && catalog.length === master.length
        && catalog.every((item) => typeof item === "string" && item.trim());
      return ok ? catalog.slice() : master.slice();
    }
    if (master && typeof master === "object") {
      const out = {};
      for (const key of Object.keys(master)) {
        out[key] = mergeCatalog(master[key], catalog && typeof catalog === "object" ? catalog[key] : undefined);
      }
      return out;
    }
    return typeof catalog === "string" && catalog.trim() ? catalog : master;
  }

  // Latin technical runs ("/config", "3_UID_SERVER", "ACCOUNT_TOKEN", URLs) but not "{placeholders}".
  const LATIN_RUN = /(?<![{\w\/])[A-Za-z0-9_\/][A-Za-z0-9_\/.:-]*(?<![.:-])(?![}\w])/g;

  /** For right-to-left pages: isolate Latin runs so "/config" is not displayed as "config/". */
  function isolateLatin(catalog) {
    if (Array.isArray(catalog)) return catalog.map(isolateLatin);
    if (catalog && typeof catalog === "object") {
      const out = {};
      for (const [key, value] of Object.entries(catalog)) out[key] = isolateLatin(value);
      return out;
    }
    return typeof catalog === "string"
      ? catalog.replace(LATIN_RUN, (run) => (/[A-Za-z0-9]/.test(run) ? `\u2068${run}\u2069` : run))
      : catalog;
  }

  const api = { resolveLanguage, mergeCatalog, isolateLatin, ALIASES };
  root.EndfieldI18n = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
