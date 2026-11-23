/* KI-tekster som hentes etter at siden er vist (E3-S04, E3-S05; PRD FR11a, spec-valg S7).
   Gjelder hver region med data-ki-url: begrunnelsen på skjerm C (#begrunnelse-svar) og briefen på skjerm A
   (#brief-svar). Siden er allerede vist med «Henter …» i en aria-live-region. Her hentes svaret med POST, og bare
   innholdet i regionen byttes, så skjermlesere får det lest opp. Feiler hentingen, vises mal-teksten (data-ki-mal)
   med merket «Testmodus (ekte kall feilet)». Uten JavaScript viser <noscript> mal-teksten merket «Testmodus».
   data-ki-klasse er klassen på teksten (standard «begrunnelse-tekst»). */
(function () {
  "use strict";

  function hent(region) {
    var url = region.getAttribute("data-ki-url");
    var mal = region.getAttribute("data-ki-mal") || "";
    var klasse = region.getAttribute("data-ki-klasse") || "begrunnelse-tekst";
    if (!url) {
      return;
    }

    function vis(merke, tekst) {
      var m = document.createElement("p");
      m.className = "ki-merke";
      m.textContent = merke;
      var t = document.createElement("p");
      t.className = klasse;
      t.textContent = tekst;
      region.replaceChildren(m, t);
    }

    var avbryt = typeof AbortController === "function" ? new AbortController() : null;
    var tidsfrist = avbryt ? setTimeout(function () { avbryt.abort(); }, 20000) : null;

    fetch(url, {
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
        vis("Testmodus (ekte kall feilet)", mal);
      })
      .then(function () {
        if (tidsfrist) {
          clearTimeout(tidsfrist);
        }
      });
  }

  var regioner = document.querySelectorAll("[data-ki-url]");
  for (var i = 0; i < regioner.length; i++) {
    hent(regioner[i]);
  }
})();
