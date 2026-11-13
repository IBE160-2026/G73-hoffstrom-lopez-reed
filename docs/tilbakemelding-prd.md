# Tilbakemelding på PRD

| | |
|---|---|
| **Gruppe** | G73 – G73-hoffstrom-lopez-reed |
| **PRD vurdert** | `docs/prd.md` (status: aktiv, sist endret 2026-10-27, commit 9c7132e). Lest sammen med `docs/addendum.md`. |
| **Dato** | 2026-11-12 |
| **Type** | Formativ tilbakemelding, ikke karakter |

## 1. Samlet inntrykk

Dette er en sterk PRD med egen tese og ærlig scope. Dere sier selv at v1 på baseline ikke kan peke ut anløp vakta bør mistro, og at et negativt modellresultat skal rapporteres like tydelig som et positivt. Risikoen ligger mest i KI-laget (feilhåndtering og kostnad), i at suksess for modellen mangler en margin, og i at PRD-en ikke har noen brukerreise som UX og stories kan hente fra.

## 2. Dette fungerer godt

- **Ærlig tese og prioritering.** §1 rangerer tre leveranser med «Hvis den glipper»-kolonne, og sier: «v1 kan *ikke* si hvilke anløp vakta bør mistro». Det gjør at epics kan kuttes uten å ødelegge helheten.
- **Lekkasjekravet er et ekte krav.** FR9a definerer kuttpunktet `t_H = rapportert ETA − H`, begrunner det og gir en test: «prediksjonen er uendret når alle AIS-punkter etter `t_H` fjernes». Slik bør et FR se ut.
- **Kjørbarhet og tall som regresjonstest.** NFR1 (under 20 minutter, versjonert utdrag, testmodus) svarer direkte på briefen. FR8 og NFR3 gjør baselinetallene (46,6 %, 79,6 %) til tester, og ordlisten (§3) gir hvert begrep ett navn.

## 3. Oversikt per dimensjon

| Dimensjon | Vurdering | Kort begrunnelse |
|---|---|---|
| Beslutningsklarhet | sterk | Valg og avveininger er synlige, f.eks. konsistens framfor ferskhet ved 6 t og bevisste avvik fra briefen (§7). |
| Substans | sterk | Alt er knyttet til dette produktet. Ingen pynte-personas eller boilerplate-NFR-er. |
| Strategisk sammenheng | sterk | Tesen om mistro-signal drar leveransene i samme retning, og modell mot baseline er selve testen. |
| Testbarhet | god | De fleste FR-ene har konkrete konsekvenser. FR5, FR6, FR7 og FR14 mangler dem, og KI-laget mangler feiltilfeller. |
| Scope og avgrensning | god | Tydelig §7 og prioritert rekkefølge. Mangler en vurdering av om E2, E3 og AA-krav rekker i tide. |
| Brukbarhet for neste fase | god | Ordliste og ID-er er stort sett konsekvente. Brukerreiser og suksessmål med ID-er mangler. |
| Formtilpasning | god | Passer et dashbord for én rolle. Men PRD-en er tett (ca. 3 000 ord) og blander krav og filnavn. |

## 4. Viktigste forbedringer

### 4.1 Modellens suksesskriterium har ingen margin
- **Alvorlighet:** medium
- **Hvor:** FR10: «modellen lykkes hvis den har høyere andel innenfor ±30 min enn baselinen på Øvrige»
- **Problem og hvorfor det betyr noe:** Med n = 996 (Øvrige) kan en forskjell på noen få anløp skyldes tilfeldigheter, og «høyere» teller også 0,1 prosentpoeng. Tilsvarende for varsel: F1 over 0,33 sier lite om modellen er nyttig for vakta. Epics og tester får da ikke noe tall å bygge på.
- **Forslag:** Sett en margin og rapporteringsregel, f.eks.: «Modellen lykkes på ±30 min hvis andelen er minst 3 prosentpoeng høyere enn baselinen på Øvrige for den aktuelle horisonten. Forskjellen rapporteres med 95 % konfidensintervall (bootstrap over anløp). Er forskjellen mindre enn marginen, rapporteres resultatet som «ikke påvist».»

### 4.2 KI-laget mangler feilhåndtering og kostnadsregler
- **Alvorlighet:** medium
- **Hvor:** FR11–FR13, f.eks. FR13: «Uten API-nøkkel kjører AI-laget i testmodus»
- **Problem og hvorfor det betyr noe:** Testmodus og «alle tall og skipsnavn finnes i inputen» er gode kontroller. Men PRD-en sier ikke hva som skjer når nøkkelen finnes og kallet feiler, svarer tomt eller bryter 400-tegnsgrensen, eller hva en demo kan koste. Da må arkitekt og utvikler gjette.
- **Forslag:** Legg til FR-konsekvenser, f.eks.: «Feiler språkmodellkallet eller returnerer teksten > 400 tegn eller et tall som ikke finnes i inputen, vises malteksten merket «KI utilgjengelig»; feilen logges, og siden lastes uansett på under 1 s. Svar caches per (anløp, prediktor), slik at samme vindu ikke gir nye kall. Maks antall kall per økt: {n}.»

### 4.3 Ingen brukerreise, så UX og stories mangler et felles scenario
- **Alvorlighet:** medium
- **Hvor:** §2 «Bruker og bruksituasjon», som er to avsnitt
- **Problem og hvorfor det betyr noe:** Spørsmålet vakta stiller er godt, men flyten fra vaktstart til beslutning er ikke beskrevet, og FR-ene kan ikke vise til «realizes UJ-1». UX-dokumentet må da finne opp flyten selv.
- **Forslag:** Skriv én kort reise: «UJ-1. Vakta åpner dashbordet ved vaktstart, leser forstyrrelsesbriefen (FR12), åpner det varslede anløpet (FR7), og sjekker om kai-planen må endres. Kantsituasjon: baselinen er aktiv, så briefen sier at ingen varsler finnes.» Legg gjerne til én sensor-reise (klone, start, spill av 08.10.2025). Koble så FR-ene til dem.

### 4.4 Noen FR-er er ikke testbare enda
- **Alvorlighet:** lav
- **Hvor:** FR5, FR6, FR7, FR14
- **Problem og hvorfor det betyr noe:** FR7 sier «en forklaring av hvordan prediksjonen ble laget» uten å si hva som er riktig. FR14 har ingen kriterier selv om det er valgfritt. Stories får uklare akseptansekriterier.
- **Forslag:** FR6: «Med avvik-sortering står anløpet med størst avvik øverst. Anløp uten fasit står sist.» FR7: «Detaljsiden viser alle tidspunkt fra ordlisten og forklaringsmalen med offset fylt inn for gruppen.» For FR14: «Droppes, eller får to kriterier: markør per anløp i vinduet og tekstlig ekvivalent.»

### 4.5 Ordliste og tall som kan avvike
- **Alvorlighet:** lav
- **Hvor:** §3 og §4 generelt
- **Problem og hvorfor det betyr noe:** Flere sentrale ord er brukt uten å stå i ordlisten (se kapittel 5). Dere har selv sett at tall dupliseres og avviker (12,9 → 12,8 %).
- **Forslag:** Legg inn de manglende begrepene. La FR8 vise til `data/baseline.json` som kilde i stedet for å gjenta hvert tall flere steder.

## 5. Mekaniske funn

- **Ordliste:** «Fasit», «prediktor», «tilstand» (fartøyets tilstand ved `t_H`) og «panel» brukes gjennomgående, men er ikke definert.
- **ID-er:** FR9a står før FR9 (rekkefølge), og E0 nevnes i endringsloggen men ikke i leveransetabellen. Det finnes ingen UJ- eller SM-ID-er.
- **Antakelser:** A1 er ikke merket `[ASSUMPTION]` inline i FR9a. A2 og A3 er merket i FR9 og FR10 og står i §9.
- **Tekniske detaljer:** FR8, NFR1 og NFR2 har filnavn og endepunkter (`/metode`, `metrikker.json`). Dette hører mest hjemme i arkitekturen.

## 6. Før dere går videre

**Må avklares før UX/arkitektur/epics:**
- Margin og rapporteringsregel for modellsuksess (4.1), før første modell trenes (§8 sier det samme).
- Hva KI-laget gjør ved feil, og kostnadsgrense (4.2), før E3-arkitekturen låses.
- Svar på A1 (var rapportert ETA kjent ved `t_24`?) og modellvalget i E2-S01.

**Kan vente:** spørsmålet om språkmodell-leverandør (E3-S03), FR14 (kart), valg av sensor-reise.

**Oppfølging av tilbakemelding på product brief:** ja. Sensor-kjøring (NFR1, versjonert utdrag og testmodus), dashbord tidlig (leveranse 1) og begrensning til låst datasett er fulgt opp. Én brief er delvis ryddet, siden §8 fortsatt viser at avvikene fra briefen skal føres inn i `brief.md`.

## 7. Refleksjonsspørsmål

1. Hvordan sjekket dere at FR9a faktisk hindrer lekkasje, og hva fant dere i KI-forslagene som måtte rettes?
2. Hvis modellen bare slår baselinen med et par prosentpoeng, hvordan avgjør dere om det er et resultat eller støy, og hva skal stå i rapporten?

_Vurdert mot kvalitetsrubrikken i bmad-prd. Dette er veiledning, ikke sensur._
