/* Begrunnelsen på skjerm C (E3-S04, PRD FR11a, spec-valg S7).
   Siden er allerede vist med «Henter forklaring …» i en aria-live-region. Her hentes svaret med POST, og bare
   innholdet i regionen byttes, så skjermlesere får det lest opp. Feiler hentingen, vises mal-teksten med merket
   «Testmodus (ekte kall feilet)». Uten JavaScript viser <noscript> mal-teksten merket «Testmodus». */
(function () {
  "use strict";
  var region = document.getElementById("begrunnelse-svar");
  if (!region || !region.dataset.url) {
    return;
  }

  function vis(merke, tekst) {
    var m = document.createElement("p");
    m.className = "ki-merke";
    m.textContent = merke;
    var t = document.createElement("p");
    t.className = "begrunnelse-tekst";
    t.textContent = tekst;
    region.replaceChildren(m, t);
  }

  var avbryt = typeof AbortController === "function" ? new AbortController() : null;
  var tidsfrist = avbryt ? setTimeout(function () { avbryt.abort(); }, 20000) : null;

  fetch(region.dataset.url, {
    method: "POST",
    headers: { "Accept": "application/json" },
    credentials: "same-origin",
    signal: avbryt ? avbryt.signal : undefined
  })
    .then(function (svar) {
      if (!svar.ok) {
        throw new Error("status " + svar.status);
      }
      return svar.json();
    })
    .then(function (data) {
      if (!data || typeof data.tekst !== "string" || typeof data.merke !== "string") {
        throw new Error("ugyldig svar");
      }
      vis(data.merke, data.tekst);
    })
    .catch(function () {
      vis("Testmodus (ekte kall feilet)", region.dataset.mal || "");
    })
    .then(function () {
      if (tidsfrist) {
        clearTimeout(tidsfrist);
      }
    });
})();
