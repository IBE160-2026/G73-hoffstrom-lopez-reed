---
title: "UX-skisser: dashbordet"
status: aktiv
created: 2026-10-16
updated: 2026-10-16
bygger_på: docs/prd.md
---

# UX-skisser — dashbordet

**Bygger på:** [`docs/prd.md`](../prd.md) (FR1–FR14, UU1–UU7). **Brukes av:** stories i [`docs/epics.md`](../epics.md). Hver skjerm under er merket med kravene og storyene den dekker.

Skissene er ASCII-wireframes med vilje. De kan ligge i git, de kan diffes, og de oppdateres i samme PR som koden når noe endres underveis. Når dashbordet finnes, legges skjermbilder av den faktiske appen i `docs/ux/skjermbilder/` ved siden av skissene (E1-S17). Avvikene mellom skisse og resultat er i seg selv designspor.

## 1. Designspørsmål og svar (16.10.2026)

Før skissene ble tegnet, stilte designeren (Claude, i UI/UX-rollen) gruppa disse spørsmålene. Svarene styrer resten av dokumentet.

| Spørsmål | Svar | Konsekvens for designet |
|---|---|---|
| Hvordan skal historikk «spilles av» når prediksjonene har 6 t/24 t-horisont? | **Simulert «nå» + 24 t-vindu.** Fasit kan slås av og på. | Tidsvelger er hovedkontrollen. Fasit er av som standard, slik vakta ville sett det. |
| Hvor brukes dashbordet? | **Desktop først, mobil skal fungere.** | Tabell på ≥ 640 px, kort under. Designet for 1280 px og testet på 360 px. |
| Hva står øverst i lista? | **Kronologisk, med avvik markert.** Sorteringen kan byttes. | Lista følger kaiplanen. Varsel er en egen kolonne med ikon og tekst. |
| Teknologi? | **Python/Flask med server-rendret HTML.** | Skjemaer og lenker i stedet for JS-interaksjon. Alt fungerer uten JavaScript og med tastatur. Tilstanden ligger i URL-en, så den kan bokmerkes og testes. |

**Funn fra dataene som påvirker designet:**

- Baselinen forskyver hver ETA med en konstant (44,8 min for passasjer, 64,2 min for øvrige). Den kan derfor **aldri varsle** et avvik. I v1 er varselkolonnen tom med vilje, og skjermen må si det rett ut, ellers ser det ut som at alt er i orden.
- «Passasjer» er en *proxy* for rutegående og inneholder cruiseskip (ROTTERDAM, MSC POESIA). UI-et kaller gruppen «Passasjer», ikke «Rutegående», for ikke å påstå mer enn dataene viser.
- Tider i data er UTC. Havnevakta tenker i norsk tid, så **all visning er Europe/Oslo**, og det står på skjermen.

## 2. Skjerm A — Hovedskjerm, desktop (≥ 1024 px)

**Dekker:** FR1–FR6, FR8, UU1–UU7 · **Stories:** E1-S06–S08, E1-S12–S13

Standardtilstand: «nå» = ons 08.10.2025 08:00, fasit av. Radene er de ekte anløpene i vinduet.

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ [Hopp til anløpslista]   ← første Tab-stopp, synlig bare ved fokus                    │
│ ANKOMSTPREDIKSJON · BERGEN HAVN                                       Avspilling av    │
│ <h1>Anløp de neste 24 timene</h1>                                     historiske data  │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ <form method=get>                                                                     │
│  Dato «nå»        Klokkeslett      Vis                          ☐ Vis faktisk ankomst │
│  [08.10.2025 ▾]   [08:00    ]      (•) Alle                                           │
│  Testperioden:                     ( ) Passasjer               [  Oppdater  ]         │
│  14.09.25–15.03.26                 ( ) Øvrige (ikke-rutegående)                       │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ Prediktor: ■ KALIBRERT BASELINE  — rapportert ETA justert med median liggetid.        │
│            Baselinen kan ikke varsle avvik. Varselkolonnen fylles når modellen kommer.│
├──────────────────────────────────────────────────────────────┬────────────────────────┤
│ 15 anløp · ons 08.10 08:00 – tor 09.10 08:00 (norsk tid)     │ TREFFSIKKERHET         │
│                                                              │ hele testperioden      │
│ Skip ▲▼        Gruppe     Rapportert  Predikert▼  Horis.  Varsel│                     │
│ ───────────── ────────── ─────────── ─────────── ─────── ────── │ Øvrige (hovedtall)  │
│ ROTTERDAM      Passasjer  ons 08:00   ons 07:15*  –       –     │ Innenfor ±30 min    │
│ EINARSON       Fisk       ons 09:00   ons 07:55*  –       –     │ ██████████░░ 46,6 % │
│ TROLLFJORD     Passasjer  ons 10:00   ons 09:15   ≤ 6 t   –     │ Naiv ETA: 12,9 %    │
│ BERGEN ENERGY  Tank       ons 11:00   ons 09:55   ≤ 6 t   –     │ Passasjer (kontroll)│
│ VASCO DA GAMA  Passasjer  ons 11:00   ons 10:15   ≤ 6 t   –     │ ███████████░ 79,6 % │
│ ELEKTRON       Last       ons 11:30   ons 10:25   ≤ 6 t   –     │                     │
│ STAVANGERFJORD Passasjer  ons 13:06   ons 12:21   ≤ 6 t   –     │ Hva betyr tallene?  │
│ OCEAN RESPONSE Last       ons 13:45   ons 12:40   ≤ 6 t   –     │ (lenke til metode)  │
│ ELDJARN        Fisk       ons 14:00   ons 12:55   ≤ 6 t   –     │                     │
│ …                                                               │                     │
│ SIEM PEARL     Slep       ons 16:30   ons 15:25   6–24 t  –     │                     │
│ MSC POESIA     Passasjer  tor 07:00   tor 06:15   6–24 t  –     │                     │
├──────────────────────────────────────────────────────────────┴────────────────────────┤
│ «–» i Varsel: baselinen varsler ikke. Skipsnavn er lenke til detaljside.             │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

**Merknader:**

- **Utvalg i vinduet:** anløp med *rapportert* ETA i [nå, nå + 24 t]. Sorteringen følger *predikert* ankomst. Predikert kan derfor ligge før «nå» (ROTTERDAM og EINARSON, merket `*`). Raden vises da med «–» i horisont og hjelpeteksten «predikert før valgt tidspunkt».
- **Horisont:** ≤ 6 t / 6–24 t fra «nå» til predikert ankomst. Det er her 6 t- og 24 t-modellene fra E2 kobles inn.
- **Skjemaet sendes bare med «Oppdater».** Det sendes ikke automatisk når et felt endres (WCAG 3.2.2), så tastatur- og skjermleserbrukere ikke får siden lastet på nytt midt i utfyllingen.
- **Tilstand i URL:** `/?naa=2025-10-08T08:00&vis=alle&fasit=0&sorter=predikert`. Den kan bokmerkes, deles og testes med Flask-klienten.
- **Prediktor-stripa** (FR3) er alltid synlig, også når modellen er i bruk. Da står det «MODELL v1 (6 t / 24 t)», og varselteksten forsvinner.
- **Treffsikkerhet** er for hele testperioden, ikke for vinduet. 15 anløp er for få til et meningsfullt tall, og panelet sier det med «hele testperioden».

### A2 — Samme skjerm med fasit på

**Dekker:** FR4, FR6, UU3 · **Stories:** E1-S09, E1-S10

```
│ Skip ▲▼        Gruppe     Rapportert  Predikert   Faktisk    Avvik ▲▼        Varsel │
│ ───────────── ────────── ─────────── ─────────── ────────── ─────────────── ────── │
│ ROTTERDAM      Passasjer  ons 08:00   ons 07:15   ons 06:28  −47 min           –    │
│ BERGEN ENERGY  Tank       ons 11:00   ons 09:55   ons 13:18  ▲ +3 t 22 min     –    │
│                                                              FORSINKET              │
│ OCEAN RESPONSE Last       ons 13:45   ons 12:40   ons 20:06  ▲ +7 t 25 min     –    │
│                                                              FORSINKET              │
│ SIEM PEARL     Slep       ons 16:30   ons 15:25   ons 22:02  ▲ +6 t 36 min     –    │
│                                                              FORSINKET              │
│ G O SARS       Auxiliary  ons 16:00   ons 14:55   ons 10:39  −4 t 16 min       –    │
│ (rad uten AIS) Tank       …           …           Fasit mangler (ingen AIS-data)   │
```

- **FORSINKET** er ikon (▲) + tekst + varselfarge (`--varsel`). Fargen er aldri alene (UU3).
- Avvik = faktisk − predikert. Positivt betyr senere enn predikert. Over 120 min gir FORSINKET (beslutning 06). Tidlig ankomst, som G O SARS, får ikke merke. Det er et bevisst valg fra beslutning 06.
- Med fasit på blir tre av fire forsinkede anløp i vinduet synlige, mens varselkolonnen er tom. *Det* er demoens poeng i v1: dette er hullet modellen skal tette.
- Kolonnen «Avvik» blir sorterbar. Sorteringsknappen ligger i `<th>` med `aria-sort`.

## 3. Skjerm B — Hovedskjerm, mobil (< 640 px)

**Dekker:** UU6 · **Story:** E1-S14

```
┌──────────────────────────────────┐
│ Anløp de neste 24 timene         │
│ ▸ Velg tidspunkt og filter       │  ← <details>, lukket som standard
│   (08.10.2025 08:00 · Alle)      │
├──────────────────────────────────┤
│ Prediktor: KALIBRERT BASELINE    │
│ Varsler ikke avvik. Mer ›        │
├──────────────────────────────────┤
│ 15 anløp · ons 08:00 → tor 08:00 │
│ ┌──────────────────────────────┐ │
│ │ ROTTERDAM          Passasjer │ │
│ │ Predikert   ons 07:15        │ │
│ │ Rapportert  ons 08:00        │ │
│ │ Horisont ≤ 6 t   Varsel –    │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ BERGEN ENERGY           Tank │ │
│ │ Predikert   ons 09:55        │ │
│ │ Rapportert  ons 11:00        │ │
│ │ Faktisk     ons 13:18        │ │  ← bare med fasit på
│ │ ▲ +3 t 22 min  FORSINKET     │ │
│ └──────────────────────────────┘ │
│ …                                │
├──────────────────────────────────┤
│ Treffsikkerhet (testperioden)    │
│ Øvrige: 46,6 % innenfor ±30 min  │
│ Passasjer: 79,6 %                │
└──────────────────────────────────┘
```

- Samme HTML-tabell som på desktop, men stilt om til kort med CSS (`display: block` per rad, `data-label` for kolonnenavn). Ingen egen mobilversjon å vedlikeholde, og skjermlesere ser fortsatt en tabell.
- Treffsikkerhet flyttes under lista. Vakta på mobil vil se anløpene først.
- Klikkflater ≥ 44 × 44 px.

## 4. Skjerm C — Detaljside for ett anløp

**Dekker:** FR7, (FR11 i E3) · **Stories:** E1-S11, E3-S04

`/anlop/3391094?naa=2025-10-08T08:00&fasit=1`

```
┌───────────────────────────────────────────────────────────┐
│ ‹ Tilbake til anløpslista (beholder nå/filter/fasit)      │
│ <h1>BERGEN ENERGY</h1>                                    │
│ Tank · MMSI 257… · Seilas 3391094                         │
├───────────────────────────────────────────────────────────┤
│ Tidspunkt (norsk tid)                                     │
│   Rapportert ETA ........ ons 08.10 11:00                 │
│   Predikert ankomst ..... ons 08.10 09:55                 │
│   Faktisk ankomst ....... ons 08.10 13:18  (fasit)        │
│   Avvik ................. ▲ +3 t 22 min  FORSINKET        │
├───────────────────────────────────────────────────────────┤
│ Slik ble prediksjonen laget                               │
│   Kalibrert baseline: rapportert ETA − 64 min.            │
│   64 min er median tid fra sonegrense til kai for         │
│   øvrige (ikke-rutegående) skip i treningsdata.           │
│   Metode: beslutning 04 ›                                 │
├───────────────────────────────────────────────────────────┤
│ [E3] Hvorfor avvik er ventet            KI-GENERERT       │
│   «…» (testmodus: lagret svar fra 2026-12-0x)             │
├───────────────────────────────────────────────────────────┤
│ [E3, valgfritt] Kart  — alt: «Kart over innseiling til    │
│   Bergen. Samme info som tabellen over.»                  │
└───────────────────────────────────────────────────────────┘
```

- «Tilbake» beholder hele spørringen. Vakta mister ikke plassen sin.
- Ukjent seilas-ID gir 404 med lenke tilbake, ikke en stacktrace.
- Datalistene er `<dl>`, ikke en tabell. Det er semantisk riktig for nøkkel–verdi.

## 5. Tilstander og feil

**Dekker:** FR1, UU5 · **Stories:** E1-S07, E1-S06

```
Ugyldig tidspunkt:                         Tomt vindu:
  Dato «nå»                                 0 anløp · lør 01.11 03:00 – søn 02.11 03:00
  [01.06.2025]                              ┌────────────────────────────────────────┐
  ⚠ Datoen må være innenfor testperioden    │ Ingen anløp med rapportert ETA i dette │
    14.09.2025–15.03.2026.                  │ vinduet. Prøv et annet tidspunkt.      │
  (feltet får aria-invalid og               └────────────────────────────────────────┘
   aria-describedby til meldingen,
   og fokus flyttes til første feil)
```

| Tilstand | Hva brukeren ser |
|---|---|
| Ingen `naa` i URL | Standard: 08.10.2025 08:00 |
| `naa` utenfor testperioden eller ugyldig | Skjemaet med feilmelding over (UU5). Lista viser standardtidspunktet, ikke ingenting. |
| 0 anløp i vinduet | Boksen over |
| Anløp uten AIS (`status_in_area ≠ ok`) | «Fasit mangler (ingen AIS-data)» i fasitkolonnene |
| [E2] Modellartefakt mangler | Faller tilbake til baseline, og prediktor-stripa sier «Modell ikke funnet — viser kalibrert baseline» |
| [E3] Ekte modus feiler (nett/nøkkel) | Viser testmodus-tekst med merket «Testmodus (ekte kall feilet)» |

## 6. Sjekkliste for universell utforming

Kjøres manuelt i E1-S15 og på nytt før levering (fase 6). Resultat og dato føres i tabellen. Automatiske tester dekker det de kan (se kolonnen «Test»).

| Krav | Sjekk | Test | Resultat |
|---|---|---|---|
| UU1 | Alle tokenpar under ≥ 4,5:1 (tekst) / 3:1 (kant) | `tests/test_kontrast.py` | |
| UU2 | Hele skjerm A og C kan brukes med bare tastatur. Fokus synlig hele veien. Hopp-lenke virker. | manuell | |
| UU3 | Skjermbilde i gråtoner: FORSINKET og varsel kan fortsatt skilles ut | manuell | |
| UU4 | Alle `<img>`/`<svg>` med mening har tekstalternativ | `tests/test_uu_struktur.py` | |
| UU5 | Alle `<input>` har `<label for>`, og feil har `aria-describedby` | `tests/test_uu_struktur.py` | |
| UU6 | 360 px, 1280 px, 1920 px og 200 % zoom uten horisontal rulling | manuell + skjermbilder | |
| UU7 | `lang="nb"`, én `h1`, `th scope`, `aria-sort`, landemerker | `tests/test_uu_struktur.py` | |
| — | Skjermleser (VoiceOver): les opp én rad og detaljsiden | manuell | |

**Tastaturrekkefølge, skjerm A:** hopp-lenke → dato → klokkeslett → filter (piltaster i radiogruppa) → fasit → Oppdater → sorteringsknapper → skipsnavn (rad for rad) → «Hva betyr tallene?».

## 7. Visuelt språk

Nøkternt kontrollrom-uttrykk: mye luft, én aksentfarge og varselfarge bare der noe faktisk er galt. Systemfonter (ingen nedlasting), tall med `font-variant-numeric: tabular-nums` så klokkeslett står rett under hverandre. Lyst tema som standard, mørkt via `prefers-color-scheme` for nattevakt.

Kontrasten er regnet ut mot `--bakgrunn` / `--flate`. Testen i E1-S13 regner det samme fra `style.css`.

| Token | Lys | Kontrast | Mørk | Kontrast | Bruk |
|---|---|---|---|---|---|
| `--bakgrunn` | `#FFFFFF` | — | `#12161A` | — | side |
| `--flate` | `#F3F5F7` | — | `#1C2228` | — | paneler, kort |
| `--tekst` | `#1A1F24` | 16,6 / 15,2 | `#E8ECEF` | 15,3 / 13,5 | brødtekst |
| `--dempet` | `#4A5560` | 7,6 / 7,0 | `#A9B4BE` | 8,6 / 7,6 | hjelpetekst |
| `--aksent` | `#0B5CAD` | 6,7 / 6,1 | `#6CB2F5` | 8,1 / 7,1 | lenker, fokusring, prediktor-merke |
| `--varsel` | `#A4262C` | 7,3 / 6,6 | `#FF8A80` | 8,0 / 7,0 | FORSINKET, varsel |
| `--ok` | `#1E6B3A` | 6,5 / 6,0 | `#7BD08F` | 9,8 / 8,6 | treffsikkerhet-søyle |
| `--kant` | `#7A8590` | 3,8 / 3,4 | `#6B7783` | 4,0 / 3,5 | skjemafelt, tabellinjer |

Fokusring: 3 px `--aksent` med 2 px avstand, aldri `outline: none` uten erstatning.

## Endringslogg

- **2026-10-16** — Første versjon (E0-S02): skjerm A/A2/B/C, tilstander, UU-sjekkliste og fargetokens med utregnet kontrast.
