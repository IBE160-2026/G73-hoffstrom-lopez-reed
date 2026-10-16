# Vurderingskriterier — vårt eget arbeidsdokument

Dette er ikke en kopi av sensorveiledningen (den skal ikke ligge i repoet). Dette er vår egen, korte oversettelse av hva sensor faktisk ser etter per kriterium, skrevet så vi kan sjekke arbeidet vårt mot det underveis — ikke bare i etterkant.

**Karaktervekting:** Del 1 (mappen/produktet) = 70 %. Refleksjonsrapporten = 30 %. Se `docs/plan.md` for refleksjonsrapporten som egen leveranse.

## Del 1 — kriterier (vekt i parentes)

### 1. Prosess og KI-styring (30 %) — tyngst

Kan sensor følge en sporbar vei fra idé til ferdig kode? Det betyr: en brief som PRD-en faktisk bygger på, en PRD som arkitekturen bygger på, stories som spores til commits, og **lagrede prompts/KI-økter koblet til konkrete endringer** — ikke bare at vi brukte KI, men at vi styrte den og kan vise hvordan.

**Hvor vi står:** Sterkt på beslutningslogg (`docs/beslutninger/`) og promptlogg (`docs/prompts/`). Svakt på selve sporbarheten videre — PRD, arkitektur og epics/stories finnes ikke ennå. Uten dem er det et hull midt i kjeden, uansett hvor god briefen eller pipelinen er.

### 2. Funksjonalitet og omfang (20 %)

Er omfanget realistisk for tre personer på et semester, og er det nok til å vise reell funksjonalitet — ikke bare planer? En urealistisk ambisiøs plan som ikke blir ferdig, teller ikke bedre enn en liten, ferdig kjerne.

**Hvor vi står:** Datapipelinen er ferdig og solid (reell styrke). Risikoen ligger i resten: modell, AI-lag og dashbord skal bygges på de gjenværende ukene. Det sensor faktisk ser og kan bruke, er dashbordet — ikke pipelinen alene.

### 3. Kvalitetssikring og testing (15 %)

Finnes det konkrete, testbare regler og forventede resultater — ikke bare en følelse av at det virker? Suksesskriterier må kunne bli testtilfeller.

**Hvor vi står:** Suksesskriteriene er allerede konkrete og målbare (±30 min, presisjon/recall på >2t-flagget, se `docs/brief.md`). Det som mangler: faktiske automatiske tester av pipelinen (ankomstregler, kalibrering) — det finnes null i dag.

### 4. Design og brukeropplevelse (10 %)

Finnes det synlige spor av designarbeid — ikke bare en beskrivelse av brukeren, men hvordan grensesnittet faktisk ser ut og oppfører seg? Universell utforming nevnes konkret: kontrast, tastaturnavigasjon, alt-tekst, skjermstørrelser.

**Hvor vi står:** Brukeren (havnevakta) og situasjonen er godt beskrevet i briefen. Selve dashbordet er ikke skissert i det hele tatt ennå — se UX-steget lagt inn i `docs/plan.md`.

### 5. Kodekvalitet og arkitektur (10 %)

Er teknologivalgene begrunnet, og ikke mer komplekse enn appen faktisk trenger?

**Hvor vi står:** Pipelinen bruker bevisst bare Python standardbibliotek, CSV og lokal caching — enkle valg, begrunnet i `docs/beslutninger/`. Samme nivå av enkelhet bør gjelde dashbord- og modellvalgene.

### 6. README og kjørbarhet (10 %)

Kan sensor faktisk kjøre appen lokalt — uten gruppens egne nøkler, betalte kontoer, eller timevis venting?

**Hvor vi står:** Svakt i dag. Full datahenting tar timer og krever et offentlig API; `pipeline/data/` er gitignored. AI-laget har ingen testmodus. Dette må løses med et lite, versjonert datautdrag og en mock/testmodus for språkmodellkall — ikke etter at dashbordet er bygget, men som en forutsetning for det.

### 7. Ryddighet i repoet (5 %)

Er det tydelig hvor hemmeligheter, testdata og dokumentasjon skal ligge, og finnes det ikke utdaterte dupliserte filer liggende som forvirrer?

**Hvor vi står:** God struktur i `docs/` og `pipeline/`. Nøkler er planlagt i miljøvariabler, aldri i repoet. `brief.md` og `brief.no.md` holdes synkronisert fremover, ikke latt drifte fra hverandre igjen.

## Generelt, på tvers av kriteriene

- **"Vis det, ikke bare beskriv det."** Går igjen i nesten alle kriteriene — en plan for testing teller mindre enn faktiske tester, en beskrivelse av brukeren teller mindre enn en skisse av skjermbildet, en påstand om KI-styring teller mindre enn en lagret prompt koblet til en commit.
- **Sporbarhet er den røde tråden.** Brief → PRD → arkitektur → stories → commits → kode. Et hvilket som helst brudd i den kjeden svekker kriterium 1, uansett hvor bra hvert enkelt ledd er for seg selv.
- **Et uferdig, kjørbart produkt slår et ambisiøst, ukjørbart ett.** Kriterium 2 og 6 straffer begge et for stort omfang som ikke blir ferdig eller ikke kan testes av noen andre enn oss selv.
