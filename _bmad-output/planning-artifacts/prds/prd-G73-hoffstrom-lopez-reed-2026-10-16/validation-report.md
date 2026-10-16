# Valideringsrapport — AIS-basert ankomstprediksjon

- **PRD:** `docs/prd.md` (versjon 2026-10-16, før oppdatering)
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Kjørt:** 2026-10-16T15:47:06+02:00
- **Karakter:** Poor

## Samlet vurdering

E1-delen holder godt. Prioriteringstabellen i §1 med «hvis den glipper» per leveranse, FR1–FR8 med konkrete standardverdier og regresjonstall, UU1–UU7 og NFR1 er presise nok til at storyene i `docs/epics.md` kan testes rett fra PRD-en. Det som står i fare, er E2, altså modellen: PRD-en definerer verken horisont, informasjonskutt eller hva det vil si å «slå» baselinen på forsinket-varselet. Ingenting i dokumentet slik det står, hindrer datalekkasje. Det er alvorlig, fordi ærlig egenmåling er hele differensieringen i briefen. Gruppas nye regel (kutt AIS-sporet ved `reported_eta − H`) må inn i PRD-en, sammen med følgekravene den utløser: tidlige ankomster, horisont-bøtta i dashbordet, AIS-data i utdraget og en valideringssplitt. Først da kan E2-S01 bygge på et fast grunnlag.

Konsistensgjennomgangen (PRD mot brief, beslutninger, UX, arkitektur og epics) bekrefter at alle kjernetall stemmer med datafila. Den legger til 17 funn, 4 av dem høye. Det tyngste er at «forsinket» ville skiftet betydning da modellen byttes inn. I tillegg er flere løfter fra briefen falt ut i stillhet: dekningstall, kart og naiv baseline for passasjer.

## Vurdering per dimensjon

- Decision-readiness — adequate
- Substance over theater — strong
- Strategic coherence — adequate
- Done-ness clarity — thin
- Scope honesty — thin
- Downstream usability — adequate
- Shape fit — strong

## Funn etter alvorlighet

### Critical (1)

**[Done-ness clarity]** — Horisont og informasjonskutt er ikke definert, og ingenting i PRD-en hindrer lekkasje (§3 FR9, §5 NFR3, §7 spørsmål 1)  
FR9 sier bare at modellen leverer «predikert ankomst og et forsinket-varsel». Det står ikke hvilke data en 6 t- eller 24 t-prediksjon kan bruke, og ikke hvordan det testes. Uten en regel kan et AIS-vindu forankret i faktisk ankomst (`arrival_in_area − H`) snike seg inn i trening eller evaluering, og da blir tallene meningsløst gode.  
Fix: Legg inn et eget krav, for eksempel «FR9a — Informasjonskutt»: *For horisont H ∈ {6 t, 24 t} er kuttpunktet `t_kutt = eta_reported − H`. Features bygges bare fra AIS-punkter med tidsstempel ≤ `t_kutt` og fra historiske anløp med `arrival_in_area < t_kutt`. Kuttpunktet forankres aldri i faktisk ankomst.* Test: å flytte eller fjerne alle AIS-punkter etter `t_kutt` endrer ikke prediksjonen.

### High (10)

**[Decision-readiness]** — Det finnes ikke noe kriterium for om modellen har lyktes på forsinket-varselet (§3 FR10, §1 rad 2)  
FR10 krever at «presisjon/recall på forsinket-varselet» vises, men det står ingen terskel og ingen sammenligning. Baselinen har `kan_varsle = False`, så den har ingen presisjon/recall å tape mot. Briefens «materially better» blir dermed uprøvbart, og gruppa kan i praksis definere suksess i etterkant, som er nettopp det briefen sier den ikke skal gjøre.  
Fix: Legg til et kriterium i FR10 med en eksplisitt referanse, for eksempel en naiv klassifikator med samme varselrate som basisraten (24,3 % for ikke-rutegående), eller recall ved fast presisjon. Rapporter tallene per horisont (6 t / 24 t) og per gruppe, og skriv kriteriet inn før E2-S03.

**[Strategic coherence]** — Testsplitten er både utviklingssett og sluttdommer (§5 NFR3)  
«Alle tall regnes på testsplitten» er riktig for rapporterte tall, men PRD-en sier ingenting om hvor features, modellvalg (åpent spørsmål 2 i §7) og hyperparametre skal velges. Arkitekturen kjenner bare `train`/`test` (arkitektur §4). E2-S01 til E2-S08 itererer mot de samme 1 566 testradene, så det endelige tallet vil være optimistisk, og sensor kan ikke se det.  
Fix: Legg til i NFR3 at modellvalg og tuning bare skjer på en kronologisk valideringsdel av `train`, for eksempel de siste 20 %, og at testsplitten kjøres én gang per modellversjon som rapporteres. Antall testkjøringer logges i resultatnotatet (E2-S09).

**[Done-ness clarity]** — Det er ikke definert hva som skjer når skipet allerede har ankommet før kuttpunktet (ingen PRD-plassering, følger av C1)  
Når `arrival_in_area ≤ eta_reported − H`, altså når skipet kommer mer enn H tidlig, ligger ankomsten selv i sporet før kuttet. Da kan modellen «se» fasiten, eller sporet ligger allerede i sonen. Beslutning 06 bekrefter at slike tidlige ankomster finnes i halen.  
Fix: Bestem og skriv i FR9a om slike anløp skal ekskluderes fra trening og evaluering, med antall logget per horisont, eller rapporteres som egen klasse («allerede ankommet»). Sett også krav om at antallet vises i resultatnotatet (E2-S09).

**[Done-ness clarity]** — Horisont-bøtta i dashbordet er udefinert og kan lekke i avspillingen (§3 FR2: «horisont (≤ 6 t / 6–24 t)»)  
FR2 sier ikke hva horisonten måles fra. E1-S06 definerer den fra *predikert* ankomst, og E2-S04 sier at «Dashbordet velger modell etter horisont-bøtta». Med kuttregelen gir det lekkasje. Et anløp med rapportert ETA ved «nå» + 8 t og predikert ankomst ved «nå» + 5 t havner i ≤ 6 t-bøtta. Da brukes 6 t-modellen med `t_kutt` = «nå» + 2 t, altså AIS-data fra *framtida* sett fra simulert «nå».  
Fix: Definer i FR2 at horisont = `eta_reported − nå` (bøtte ≤ 6 t: 6 t-modell, 6–24 t: 24 t-modell). Det sikrer `t_kutt ≤ nå` for alle rader. Legg til en akseptansetest om at ingen prediksjon i avspillingen bruker data etter «nå», og oppdater E1-S06 og E2-S04.

**[Scope honesty]** — En umarkert antakelse er at rapportert ETA var kjent ved kuttpunktet (§3 FR2, FR9; §7 spørsmål 1)  
Datasettet har «én rapportert ETA per seilas», uten tidspunkt for når den ble rapportert eller sist oppdatert (arkitektur §4 har bare `eta_reported`). Er verdien den *siste* ETA-en før anløp, er den selv informasjon fra etter `reported_eta − H`. Da lekker både kuttankeret og baselinen, og «nå»-avspillingen i FR2 viser en ETA vakta ikke hadde.  
Fix: Marker `[ASSUMPTION: eta_reported er kjent senest ved eta_reported − 24 t]`, verifiser mot Kystdatahuset-dokumentasjonen eller rådata i E2-S01, og skriv begrensningen i resultatnotatet hvis den ikke kan verifiseres.

**[Downstream usability]** — AIS-sporet finnes ikke i datautdraget, og kuttregelen kolliderer med NFR1 (§5 NFR1; arkitektur §4)  
Kuttregelen forutsetter AIS-posisjoner per anløp ved kjøring, for `ModellPrediktor.prediker(anlop, naa)` i avspillingen. `data/utdrag/anlop.csv` har bare `voyageid, mmsino, shipname, ship_group, eta_reported, arrival_in_area_utc, status_in_area, split`, og NFR1 forbyr nett og `pipeline/data/`. PRD-en sier ingenting om hvordan modellen får inputen sin hos sensor.  
Fix: Legg til under NFR1 «Fra E2:» enten et versjonert utdrag av ferdigberegnede features per anløp og horisont (beregnet med kuttregelen, med sjekksum) eller forhåndsberegnede prediksjoner. Sett en størrelsesgrense i samme stil som arkitekturens 10 MB.

**[Konsistens]** — Forsinket-merket endrer betydning når modellen byttes inn (§3 FR4 ↔ ux/dashbord.md §2 A2 ↔ beslutning 06)  
FR4 sier bare «avvik i minutter og et forsinket-merke (> 2 t, se beslutning 06)». Beslutning 06 definerer flagget mot *kalibrert baseline*: `er_forsinket = (kalibrert arrival_in_area − rapportert_eta) > 120 min`. Arkitektur §4 følger det («regnes ut i appen fra baselinen»). UX A2 sier derimot «Avvik = faktisk − predikert … Over 120 min gir FORSINKET». Med baseline gir dette samme tall. Med modellen (E2-S07) ville fasit-merket blitt regnet mot modellens egen prediksjon. Da endrer sannhetsetiketten seg med prediktoren, og presisjon/recall i FR10 blir umulig å tolke.  
Fix: Skriv i FR4 at «Avvik» og FORSINKET alltid regnes mot kalibrert baseline (beslutning 06), uansett aktiv prediktor. Rett UX A2, og legg til en test i E2-S07 som sjekker at fasit-merkene er like med `PREDIKTOR=baseline` og `PREDIKTOR=modell`.

**[Konsistens]** — Halen modellen skal slå er ikke den samme halen som flagget måler (§3 FR10 ↔ brief Success Criteria «24.3 %» ↔ beslutning 06)  
Briefen sier at modellen skal gi bedre presisjon/recall på «that ~24% disruption tail». Når jeg regner etter, er 24,3 % andelen med *absolutt* kalibrert avvik > 120 min (øvrige, testsplitt, n=996). `er_forsinket` er signert (beslutning 06) og har bare **19,5 %** positive på de samme radene. PRD-en nevner ikke tallet i det hele tatt og arver dermed avviket i stillhet.  
Fix: Ta grunnraten inn i FR10: «19,5 % av øvrige anløp i testsplitten er forsinket (> 120 min, signert)». Si at 24,3 % i briefen er tosidig, og meld det tilbake som en rettelse i brief/addendum.

**[Konsistens]** — Dekning og datakvalitet per kjøring er falt ut (§3 FR8, §5 NFR3 ↔ brief Data Out «Coverage and data-quality metrics shipped with every run, not hidden», brief Success Criteria «Data quality», brief Scope IN 2)  
Ingen FR eller NFR krever at dekningen vises. E1-S05 regner «bare på anløp med fasit», men panelet oppgir ikke n eller hvor mange som falt bort. På testsplitten har 139 av 1 566 rader ikke status `ok`: 126 `empty`, 8 `not_detected` og 5 `avkortet_av_neste_seilas`. Det gir en testdekning på 91,1 %, mot 87,1 % for hele datasettet. Beslutning 02 krever at `avkortet_av_neste_seilas` «telles og rapporteres separat».  
Fix: Legg til et krav, for eksempel FR8b: panelet og `/metode` viser n med fasit / n totalt per gruppe og antall per status, regnet med `metrikker.py`. Spor kravet til E1-S12 og E2-S05 (`metrikker.json`).

**[Konsistens]** — Kart og «daily brief» er nedprioritert uten at avviket fra briefen er notert (§3 FR12/FR14, §6 ↔ brief Scope IN 4 «predicted arrivals, a map, and a stated reason per expected deviation», brief The Solution «a map plus a stated reason»)  
Briefen har kartet i v1-scope. PRD FR14 gjør det til «lavest prioritet i hele prosjektet og kan droppes». FR12 gjør dagsbriefen om til en brief for 24 t-vinduet. Det kan være et fornuftig valg, men §6 sier «Som i briefens Scope/OUT», og endringsloggen nevner det ikke. I tillegg kan kartet ikke bygges på det planlagte grunnlaget: utdraget i arkitektur §4 har ingen posisjonskolonner, og E3-S08 sier selv «Utdraget har ingen posisjoner».  
Fix: Før opp kartet i §6, eller som en eksplisitt nedprioritering med begrunnelse. Gjør det samme i endringsloggen, og oppdater brief Scope IN 4 (og brief.no.md) så kjeden stemmer.

### Medium (16)

**[Decision-readiness]** — Åpent spørsmål 1 i §7 er avgjort, men PRD-en er ikke oppdatert  
Gruppa har bestemt at horisonten defineres ved å kutte sporet ved `reported_eta − H`. PRD-en kaller seg «levende» og sier at krav «endres her først», men både §7 og endringsloggen mangler beslutningen.  
Fix: Flytt spørsmålet til et nytt krav (se Done-ness, C1), lenk til `docs/beslutninger/08-…` og skriv en linje i endringsloggen.

**[Strategic coherence]** — Dashbord v1 kan ikke oppfylle målet i §1 (§1 Mål mot FR3)  
Målet lover hvilke anløp vakta bør «mistro, og hvorfor», men leveranse 1, den eneste som «kan ikke glippe», viser «–» i varselkolonnen for alle rader. PRD-en sier ikke hva vakta da faktisk får ut av v1.  
Fix: Skriv én setning i §1 om hva v1 alene gir, for eksempel en kalibrert forventet ankomst og fasit-avspilling, og at mistro-signalet kommer først med E2. Da blir et E2-tap også ærlig beskrevet på produktnivå.

**[Done-ness clarity]** — Det er uklart hva «avvik» måles mot (§3 FR4, FR6)  
FR4 sier «avvik i minutter og et forsinket-merke (> 2 t, se beslutning 06)». Avvik kan bety faktisk minus predikert eller faktisk minus rapportert ETA. Beslutning 06 bruker kalibrert ankomst minus rapportert ETA, mens sortering etter «størst avvik» (FR6) sannsynligvis gjelder prediksjonsfeil.  
Fix: Skriv formelen i FR4: `avvik = faktisk ankomst − predikert ankomst` for kolonnen, og `er_forsinket` som i beslutning 06 for merket. Si at FR6 sorterer på absoluttverdien av det første.

**[Done-ness clarity]** — Regelen for forsinket-varselet og valg av modellversjon mangler (§3 FR9)  
Det står ikke om varselet er en egen klassifikator eller en terskel på predikert avvik (predikert − rapportert ETA > 120 min). Det står heller ikke hvilken horisont detaljsiden viser når begge finnes.  
Fix: Spesifiser varselregelen i FR9 og at det er bøtta fra FR2 som avgjør hvilken modell som vises.

**[Done-ness clarity]** — FR11 kan nesten ikke testes (§3 FR11)  
«En kort tekst», «generert *kun* fra modellens faktiske input og output» har ingen lengdegrense og ingen sjekkbar betingelse.  
Fix: Sett en grense, for eksempel ≤ 3 setninger eller ≤ 400 tegn. Legg til en automatisk test: alle tall og skipsnavn i teksten finnes i `forklaring` eller i `Prediksjon`. I testmodus er dette deterministisk.

**[Done-ness clarity]** — FR12 mangler en utvelgelsesregel og atferd for baseline (§3 FR12)  
Kravet sier ikke hvordan det avgjøres «hvilke anløp vakta bør følge med på», eller hva briefen sier når baselinen er aktiv og ingenting varsles.  
Fix: Definer utvalget, for eksempel anløp med `forventet_forsinket = True`, sortert etter predikert avvik, maks 3. Bestem også teksten når ingen varsler eller når kilden er baseline.

**[Done-ness clarity]** — «Demodagene» i FR13 er udefinert (§3 FR13)  
Sensor må vite hvilke dager som gir lagrede ekte svar.  
Fix: List datoene i FR13, for eksempel standarddagen 08.10.2025 og en dag med høy varseltetthet, og krev at README nevner dem.

**[Done-ness clarity]** — Briefens produktkriterium er ikke oversatt til noe sjekkbart  
Briefen sier: «The havnevakt can read a daily brief and understand, without asking anyone, which … to distrust and why.» PRD-en har ingen akseptansesjekk for dette.  
Fix: Legg en manuell sjekk under FR12, for eksempel at en person utenfor gruppa leser briefen for standarddagen og nevner riktige anløp og grunn uten hjelp. Logg resultatet.

**[Scope honesty]** — Flere ting fra briefen er tatt ut uten at det står noe sted (§2, §6)  
Briefens sekundærbruker havnekaptein/driftsleder er borte. «Coverage and data-quality metrics shipped with every run, not hidden» har ikke noe krav, selv om dekningsgraden (87,1 %) er et av prosjektets beste funn. Briefens «replay a chosen day or period» er redusert til et 24 t-vindu.  
Fix: Før disse opp i §6 som `[NON-GOAL for v1]`, eller legg til et lite krav om at dekningsgrad og antall droppede seilaser vises i treffsikkerhetspanelet (FR8).

**[Downstream usability]** — Ordliste mangler, og begrepene drifter (hele dokumentet)  
«Rutegående/ikke-rutegående» (FR2, FR5, FR8) heter «Passasjer/Øvrige» i arkitektur §4 og «passasjer/ovrige» i E1-S03/E1-S08. Varselet heter «varsel» (FR2), «forsinket-varsel» (FR9, FR10), «forsinket-merke» (FR4) og `er_forsinket` (beslutning 06). «Anløp» og «seilas» brukes om hverandre (FR2 mot §7).  
Fix: Legg inn en kort ordliste med faktisk ankomst (= `arrival_in_area`, soneinngang), rapportert ETA, kalibrert baseline, horisont, kuttpunkt, forsinket (beslutning 06), rutegående (= `ship_group` Passasjer) og anløp. Bruk ett ord per begrep.

**[Konsistens]** — MAE og median som støttetall mangler i PRD, men finnes i en story (§3 FR8/FR10 ↔ brief «Support stats only: MAE and median absolute error», beslutning 05 «MAE og median skal fortsatt beregnes og vises»)  
PRD-en nevner aldri MAE eller median. E2-S05 skriver likevel «MAE og median (som støttetall)» til `metrikker.json` og har dermed ikke noe PRD-grunnlag. Ingen story viser tallene i dashbordet eller på `/metode`, selv om beslutning 05 sier «vises».  
Fix: Legg til i FR8/FR10: «MAE og median absolutt avvik vises på `/metode` (eller i panelet), merket som støttetall». For baseline/øvrige er tallene 136 og 34,3 min. Spor kravet til E1-S12 og E2-S05.

**[Konsistens]** — Naiv baseline for passasjer mangler (§3 FR8 ↔ beslutning 04 Konsekvens «Rapportering må alltid vise både naiv og kalibrert baseline»)  
FR8 og UX-panelet viser bare naiv ETA for øvrige (12,9 %). Naiv for passasjer, 7,4 %, er utelatt, og det samme gjelder forklaringssetningen beslutning 04 krever om at forskjellen skyldes to ulike fysiske hendelser.  
Fix: Ta med «naiv 7,4 %» for passasjer i FR8 og i dataregresjonstesten (E1-S05), og krev forklaringssetningen på `/metode` (E1-S12).

**[Konsistens]** — Det er ikke definert hva det betyr at modellen «taper» på flagget (§3 FR10)  
«Taper modellen på ett eller begge mål, vises det like tydelig.» Baselinen kan ikke flagge noe (brief, beslutning 06), så det finnes ikke noen presisjon/recall å tape mot. Dermed er sekundærmålet ikke testbart (kriterium 3).  
Fix: Sett en konkret terskel eller referanse i FR10, for eksempel «recall ≥ X % ved presisjon ≥ Y %» eller «slår en enkel regel (gruppe + rapportert time)». Alternativt kan PRD-en si eksplisitt at bare tallene rapporteres, uten noe bestått/ikke bestått.

**[Konsistens]** — 6 t/24 t-prediksjon er ikke et evaluerbart krav (§3 FR2/FR9/FR10 ↔ brief Data Out «Predicted arrival time (6h and 24h horizon)», Scope IN 3)  
FR2 definerer horisonten som tiden fra «nå» til predikert ankomst, altså som en visningsbøtte. Ingen FR krever at treffsikkerheten rapporteres per horisont, men E2-S05 gjør det («per gruppe og horisont») og har da ikke noe PRD-grunnlag. Åpent spørsmål 1 i §7 erkjenner problemet, men FR-ene er ikke markert som avhengige av svaret.  
Fix: Merk FR9/FR10 med «avhenger av beslutning 08» og legg til «tall per horisont» i FR10. Ellers bør ambisjonen i briefen om to horisonter nedskaleres eksplisitt.

**[Konsistens]** — PRD-en bruker «rutegående», UX bruker «Passasjer» (§3 FR2/FR5/FR7/FR8 ↔ ux/dashbord.md §1)  
UX sier: «UI-et kaller gruppen «Passasjer», ikke «Rutegående», for ikke å påstå mer enn dataene viser» (cruiseskip inngår). PRD-en bruker «rutegående/ikke-rutegående» overalt og sier ikke at gruppen er en proxy (`ship_group == 'Passasjer'`, 2 349 rader, mot fem andre grupper). FR2 krever kolonnen «rutegående/ikke-rutegående», men skisse A viser `ship_group` (Tank, Fisk …).  
Fix: Legg til en definisjon i §3: «Passasjer = proxy for rutegående; Øvrige = alle andre ship_group». Bruk UX-navnene i FR5 og FR8, og rett FR2 til «skipsgruppe».

**[Konsistens]** — «Fasit mangler» blander sammen tre ulike årsaker (§3 FR4 ↔ beslutning 02 ↔ ux/dashbord.md §5)  
FR4 sier «Anløp uten AIS-data viser «Fasit mangler»», og UX §5 setter teksten «(ingen AIS-data)» på alle med `status_in_area ≠ ok`. Data har tre slike statuser: `empty` (935), `not_detected` (32) og `avkortet_av_neste_seilas` (44). De to siste *har* AIS. Beslutning 02 sier at de avkortede nettopp er «et ekstremavvik vi vil fange» og ikke må forsvinne stille.  
Fix: Skill mellom dem i FR4: «Fasit mangler (ingen AIS)», «Ikke funnet i vinduet» og «Avkortet av neste seilas – trolig stort avvik». Legg til en test i E1-S09.

### Low (10)

**[Done-ness clarity]** — Vindusgrensen er inkonsistent (§3 FR2)  
PRD-en har lukket intervall «[«nå», «nå» + 24 t]», mens E1-S03 har halvåpent `[naa, naa + 24 t)`.  
Fix: Bruk halvåpent intervall i PRD-en.

**[Done-ness clarity]** — Forklaringsteksten i FR7 gjelder bare én gruppe (§3 FR7)  
Eksempelteksten «rapportert ETA − 64 min, median liggetid for ikke-rutegående» dekker ikke rutegående (44,8 min). «Liggetid» er dessuten misvisende for offset fra soneinngang til kai.  
Fix: Skriv teksten som mal per gruppe: «rapportert ETA − {offset} min (median tid fra havneområde til kai, {gruppe}, treningsdata)».

**[Scope honesty]** — Det er for få `[NOTE FOR PM]`-markeringer ved reelle spenninger  
Den mest åpenbare spenningen er at 6 t-modellen i dashbordet bruker et spor som slutter opptil 6 t før «nå» (kutt ved ETA − 6 t), altså foreldet informasjon, mens kutt ved «nå» ville gitt skjevhet mellom trening og drift.  
Fix: Skriv én markering ved FR9a som sier at gruppa bevisst velger konsistens med treningen framfor ferskhet.

**[Konsistens]** — Hull i sporbarhetstabellen (epics.md «Sporbarhet: krav → stories»)  
NFR5 og NFR6 mangler i tabellen, selv om E3-S01 viser til NFR6. Tre stories har ikke noe PRD-krav: E1-S12 sin `/metode` (arkitektur §6 har ruten, PRD-en har den ikke), E2-S09 `docs/resultater.md` (spores til briefen) og E1-S17 (kriterium 4).  
Fix: Legg NFR5/NFR6 til i tabellen. Gjør `/metode` og resultatnotatet til FR-er, eller la tabellen ha en egen rad med «spores direkte til brief/kriterium».

**[Konsistens]** — Antall seilaser stemmer ikke mellom brief og PRD-kjeden (brief Scope IN 1 «8,094 voyages» ↔ arkitektur §4 «alle 7 826 rader», A2 «~7 800»)  
Datafila har 7 826 rader. PRD-en oppgir ingen n og lar avviket stå uforklart.  
Fix: Skriv én setning i PRD §1 eller §5: «Utdraget har 7 826 seilaser (8 094 hentet, se addendum for frafall)».

**[Konsistens]** — Små avvik mellom FR og story/UX i vindu og horisont (§3 FR2, FR7)  
FR2 bruker et lukket intervall «[«nå», «nå» + 24 t]», mens E1-S03 er halvåpent «[naa, naa + 24 t)». FR2 nevner ikke «–» for predikert ankomst før «nå», som UX og E1-S06 har. FR7 gir bare forklaringen for øvrige («− 64 min»), ikke for passasjer («− 45 min»).  
Fix: Rett FR2 til halvåpent intervall og legg til «–»-regelen. Gi FR7 begge gruppene.

**[Konsistens]** — Påstanden om standardvinduet i UX stemmer ikke med data (ux/dashbord.md §2 A2 «tre av fire forsinkede anløp»)  
Standardvinduet har nøyaktig tre anløp med `er_forsinket=True` (BERGEN ENERGY 202, OCEAN RESPONSE 445 og SIEM PEARL 396 min), og alle har fasit. Det finnes ikke noe fjerde. E1-S09 har riktig tall.  
Fix: Endre UX-teksten til «alle tre forsinkede anløp».

**[Konsistens]** — Brief-elementer er falt ut uten at det står i §6 (§2, §6 ↔ brief Who This Serves, Scope IN 4/5)  
Det gjelder sekundærbrukeren havnekaptein/driftsleder, avspilling av en «period» (PRD-en har bare 24 t-vindu) og HTTP Basic Auth ved fjerntilgang. Ingen av disse er nevnt som utelatt.  
Fix: Skriv én linje i §6 for hver av dem.

**[Konsistens]** — Promptlogg mangler i NFR4 (§5 NFR4 ↔ vurderingskriterier.md kriterium 1 «lagrede prompts/KI-økter koblet til konkrete endringer»)  
NFR4 dekker story–commit–PR, men ikke koblingen til `docs/prompts/`. Den står bare i arbeidsreglene i epics og i E3-S03.  
Fix: Legg til i NFR4: «PR-beskrivelsen lenker til promptloggen for øktene».

**[Konsistens]** — Ikke definert hva FR11 og FR12 bygger på hvis E2 glipper (§1 leveranse 3 ↔ §3 FR11/FR12 ↔ epics E3-S01, E3-S05)  
FR11 krever input «kun fra modellens faktiske input og output». E3-S01 tillater å bygge på E1-S04 (baseline) hvis E2 glipper. Da har E3-S05 sin test «nevner anløpene med varsel» ingen varsler å nevne.  
Fix: Si i FR11/FR12 hva AI-laget bygger på når det står på baseline, for eksempel at briefen omtaler gruppe, horisont og historisk usikkerhet.

## Mekaniske merknader

- **Kryssreferanser:** «brief, beslutning 04» i FR8 peker feil. Beslutningen ligger i `docs/beslutninger/04-kalibrert-baseline.md`, ikke i briefen. «beslutning 06» i FR4 er ikke lenket. «kriterium 1/3/5/6/7» i NFR-ene peker trolig på `docs/vurderingskriterier.md`, men har ingen lenke. «se arkitektur, §3» og lenken til UX §6 finnes og stemmer.
- **ID-kontinuitet:** FR1–FR14, UU1–UU7 og NFR1–NFR6 er sammenhengende og unike. «Beslutning 08» er reservert i §7 og i E2-S01, men FR9 viser ikke til den. Legg til lenken når den finnes.
- **Assumptions-indeks:** finnes ikke, fordi PRD-en ikke har noen `[ASSUMPTION]`-markeringer. Hvis funnet om ETA-tidspunkt (Scope honesty) blir tatt inn, bør det komme en kort indeks.
- **Endringslogg:** har bare første versjon. Beslutningen om kuttregelen må logges der (se Decision-readiness).
- **Ytelse:** ingen grense for svartid på `GET /`. Det er lav risiko med ~7 800 rader, men en grense som «< 1 s på standardvinduet» ville gitt E1-S06 et ekstra sjekkpunkt.
- **Seksjoner:** alt som trengs for denne innsatsen og produkttypen er med. Suksessmål ligger i briefen og arves. Det er greit, men FR8/FR10 bør eksplisitt si at det er de som er suksessmålene.

## Gjennomgangsfiler

- `review-rubric.md`
- `review-konsistens.md`
