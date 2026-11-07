# E2-S02–S05: full henting, utdrag, sjekker og modellspec

## 2026-11-06 kl. 10:02 — Felipe Knudstad-Lopez

### Oppgave
Felipe styrte økta fra Theodors maskin. Hentingen for E2-S02 var ferdig: 7 825 av 7 826 seilaser, og 1 feil (URLError 05.11, maskinen var uten nett). Planen var:
1. ta de seks review-rettelsene og hente den feilede seilasen
2. committe dekningstabellen og sette E2-S02 ferdig
3. sammenligne dekningen med 93 % i beslutning 09
4. lage tilstands- og featureutdragene
5. kjøre sjekken av lange avstander og etikettsjekken
6. starte E2-S05 med full BMAD-flyt og stoppe ved godkjenning

Alle commits har Felipe som forfatter.

### Plan
- Steg 1–3, stopp og vis. Deretter flytte tabellen til `data/utdrag/`, beslutning 09, push og steg 4–5, stopp og vis. Så sjekkskriptet, beslutning 03, refleksjonsnotater, push og E2-S05.
- Kontinuitet: [998 e2-s02](998-2026-11-03-18-21-12-e2-s02-ais-henting-ved-kuttpunkt.md), [996 e2-s03](996-2026-11-03-19-02-50-e2-s03-tilstandsutdrag.md), [995 e2-s04](995-2026-11-03-19-20-13-e2-s04-features.md).
- E2-S05-spec (utkast): `_bmad-output/implementation-artifacts/spec-e2-s05-tren-modell.md`.

### Resultat
- **`8694a48` E2-S02, de seks review-rettelsene, med 10 nye tester:**
  - En manglende dag som ikke kan deles, teller mot stoppregelen.
  - Vernet mot evig deling har fått tester.
  - Delkallene har fått pause.
  - Dedupen er fjernet.
  - Svaret klippes til forespørselen + 2 t. Det avviker fra funnet, som sa ved `slutt`. Begrunnelsen står i specen.
  - Det er nye tester for `tapt_intervall` og for gammel cache.
  - Mutasjonssjekk: 7 av 7 mutasjoner fanget.
  - Seilas 2713140 ble hentet på nytt, så alle 7 826 av 7 826 er i cachen (6,0 GB).
- **`46db209` E2-S02:** dekningstabellen er lagt til, og E2-S02 står til ✅.
- **`9b2e433`:** tabellen er flyttet til `data/utdrag/ais_kutt_dekning.csv`, og skriptet, epics og specen er oppdatert. Beslutning 09 har fått et avsnitt om resultatet: 93,4 % (930/996, KI 91,7–94,8) med fasit, 90,4 % for alle anløp og 65,2 % for `empty`. De samme 40 anløpene fra stikkprøven gir fortsatt 37/40, med de samme 3 som manglet. Tråden om `empty` er lukket.
- **`910028c` E2-S03:** `tilstand_ved_kutt.csv/.json`, 15 652 rader. Ved H = 6 er 6 866 `ok`, og ved H = 24 er 6 569 `ok`. `manglende_dag` er 1 ved H = 6 og 10 ved H = 24. Ny `test_committet_tilstand`, og E2-S03 står til ✅.
- **`47a2c02` E2-S04:** `features.csv/.json`, 15 652 rader, med 5 008 / 1 252 / 1 566 anløp per del. En ny kjøring ga byte-identisk fil. Ny `test_committet_features`. E2-filene er 4,2 MB til sammen. E2-S04 står til ✅.
- **`a90f1f6` E2-S04, `scripts/sjekk_avstand_og_etikett.py`:**
  - 15 rader trenger mer enn 25 kn.
  - Tre er «umulige» (HALTBAKK STAR, NORDKAPP og STAVANGERFJORD), alle i train.
  - 33 av 6 815 anløp (0,48 %) har soneinngang mer enn 24 t før ETA, spredt på 14 skipstyper. Offshore og forsyning står for 18,2 % av dem, mot 15,8 % av alle anløp. 6 av de 33 er i test.
  - Ført inn som kjent begrensning i beslutning 03, og tabellene står i E2-S04-specen.
- **`bd1dce3`:** refleksjonsnotater om de manglende committet-testene (andre gang, jf. 22.10) og om feil kallantall i review-funnet.
- Alt til og med `bd1dce3` er pushet. Testene er grønne: 263 passed.
- **E2-S05:** BMAD-build steg 1–2 er kjørt. Specen er skrevet med `status: draft` (ikke committet), med tre åpne spørsmål: valideringskriteriet, kandidatsettet, og om de 33 tidlige anløpene og de 3 umulige skal være med i treningen. Specen er omtrent 2 400 tokens, over grensen på 1 600.

### Åpne punkter
- E2-S05: Felipe svarer på de tre åpne spørsmålene i specen og avgjør om specen kan være over 1 600 tokens. Deretter godkjennes den, og implementeringen starter.
- Seilas 3353948 HALTBAKK STAR i testdelen har soneinngang 89 t før ETA (beslutning 03). Den tas med i resultatnotatet (E2-S10) som en mulig etikettfeil i testperioden.
