// Kjører app/static/begrunnelse.js mot en minimal falsk DOM og skriver resultatet som JSON (tests/test_begrunnelse_js.py).
// Bruk: node begrunnelse_harness.js <sti til begrunnelse.js>
"use strict";
const fs = require("fs");
const kilde = fs.readFileSync(process.argv[2], "utf8");

function el(tag, attrs) {
  return {
    tagName: tag, attrs: attrs || {}, children: [], className: "", textContent: "",
    getAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : null; },
    replaceChildren(...c) { this.children = c; },
  };
}

// Hvert tilfelle: regionenes attributter og hva fetch gjør.
const svarOk = (data) => () => Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
const tilfeller = {
  skjerm_c_feiler: { regioner: [{ "data-ki-url": "/anlop/1/begrunnelse", "data-ki-mal": "MAL C" }],
                     fetch: () => Promise.reject(new TypeError("Failed to fetch")) },
  brief_feiler: { regioner: [{ "data-ki-url": "/brief", "data-ki-mal": "MAL A", "data-ki-klasse": "brief-tekst" }],
                  fetch: () => Promise.reject(new TypeError("Failed to fetch")) },
  http_500: { regioner: [{ "data-ki-url": "/anlop/1/begrunnelse", "data-ki-mal": "MAL C" }],
              // Gyldig form på kroppen, så bare statusen kan gi feilgrenen.
              fetch: () => Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ tekst: "FEIL", merke: "KI-GENERERT" }) }) },
  ugyldig_svar: { regioner: [{ "data-ki-url": "/brief", "data-ki-mal": "MAL A", "data-ki-klasse": "brief-tekst" }],
                  fetch: svarOk({ tekst: 42, merke: "KI-GENERERT" }) },  // bare teksten er ugyldig
  ugyldig_merke: { regioner: [{ "data-ki-url": "/anlop/1/begrunnelse", "data-ki-mal": "MAL C" }],
                   fetch: svarOk({ tekst: "SVAR", merke: null }) },  // bare merket er ugyldig
  skjerm_c_ok: { regioner: [{ "data-ki-url": "/anlop/1/begrunnelse", "data-ki-mal": "MAL C" }],
                 fetch: svarOk({ tekst: "SVAR C", merke: "KI-GENERERT" }) },
  begge_ok: { regioner: [{ "data-ki-url": "/brief", "data-ki-mal": "MAL A", "data-ki-klasse": "brief-tekst" },
                         { "data-ki-url": "/anlop/1/begrunnelse", "data-ki-mal": "MAL C" }],
              fetch: (url) => Promise.resolve({ ok: true, json: () => Promise.resolve({ tekst: "SVAR " + url, merke: "KI-GENERERT" }) }) },
};

async function kjor(navn) {
  const t = tilfeller[navn];
  const regioner = t.regioner.map((a) => { const r = el("div", a); r.children = [{ className: "henter", textContent: "Henter …" }]; return r; });
  const kall = [];
  const document = { createElement: (tag) => el(tag), querySelectorAll: (s) => (s === "[data-ki-url]" ? regioner : []) };
  const fetch = (url, opts) => { kall.push({ url, method: opts && opts.method }); return t.fetch(url, opts); };
  new Function("document", "fetch", "AbortController", "setTimeout", "clearTimeout", kilde)(
    document, fetch, AbortController, setTimeout, clearTimeout);
  await new Promise((r) => setTimeout(r, 20));
  return { kall, regioner: regioner.map((r) => r.children.map((c) => ({ klasse: c.className, tekst: c.textContent }))) };
}

(async () => {
  const ut = {};
  for (const navn of Object.keys(tilfeller)) ut[navn] = await kjor(navn);
  process.stdout.write(JSON.stringify(ut));
  process.exit(0);
})();
