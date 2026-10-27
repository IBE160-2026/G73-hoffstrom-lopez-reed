# Refleksjonsnotater: råmateriale

Råmateriale til refleksjonsrapporten, ikke ferdig tekst. **Regel:** hver gang vi fanger noe KI-en gjorde feil eller påsto uten grunnlag, legges det inn her samme dag, med dato, hva som skjedde, hvordan det ble oppdaget og commit-hasher. Nyeste nederst.

---

## 2026-10-22 — Tidsstempeltesten fantes ikke

- **Hva:** Beslutning 09 fant at Kystdatahuset returnerer AIS-punkter fra et vindu forskjøvet +1/+2 t. Uten filtrering på tidsstemplet ville modellen fått data fra etter kuttpunktet, altså lekkasje. Kravet om filtrering og testen `test_filtrerer_bort_punkter_etter_kutt` ble skrevet inn i E2-S02 (`94330e9`). Filteret i stikkprøveskriptet sto inline og uten test. **Testen var beskrevet, men aldri implementert.**
- **Hva KI-en påsto:** I oppsummeringen etter E0-S10 skrev Claude at FR9a og E2-S02 krever filtrering «med egen test». Det kunne leses som at testen fantes.
- **Hvordan det ble oppdaget:** Gruppa ba om bevis for at testen faktisk feiler når filteret fjernes («en test som alltid er grønn beviser ingenting»). Da kom det fram at det ikke var noen test å sjekke.
- **Hva mutasjonssjekken avdekket i tillegg:**
  - Første versjon av uttrekket (`filtrer_til_vindu()`) kalte seg selv, fordi en tekstendring ble kjørt to ganger. Testen var rød allerede på den «originale» koden (RecursionError).
  - De første mutantene traff en annen linje enn funksjonen, så «rød for mutanten» betydde ingenting.
  - Det ble oppdaget fordi originalen også var rød. Uten kontrollkjøringen på originalen ville tre røde mutanter sett ut som et bevis.
- **Resultat:** Etter rettingen er testen grønn på originalen og rød for alle tre mutantene: uten filter, uten sluttgrense, og `<` i stedet for `<=` ved kuttet (`14b21e3`, E0-S12).
- **Lærdom (råt):**
  - «Spesifisert» er ikke det samme som «implementert».
  - En mutasjonssjekk må alltid ha en kontrollkjøring på uendret kode.
  - Be om bevis, ikke om bekreftelse.

## 2026-10-22 — API-tidene var aldri verifisert, selv om koden sa «verified»

- **Hva:** `pipeline/fetch_ais.py` (`ad2ffca`, 27.09) sier i docstringen at API-et er «verified against live API» og at datoene er UTC. Ingen sjekket om vinduet i svaret faktisk stemte med det vi ba om. I praksis er det forskjøvet +1 t om vinteren og +2 t om sommeren, og korte vinduer som slutter rett etter midnatt, kuttes.
- **Hvordan det ble oppdaget:** Stikkprøven til beslutning 09 ga et svar som gikk forbi `end`. Første punkt i cachen lå alltid 60 eller 120 min etter vindusstart.
- **Konsekvens:** Ankomstetikettene er ikke berørt, fordi de bruker tidsstemplene i svaret. Men en naiv kutthenting i E2-S02 ville lekket data. Se `94330e9` (beslutning 09) og `3f78c1e` (skriptene merket som låst).

## 2026-10-22 — Beslutning 07 hadde feil forklaring

- **Hva:** Beslutning 07 (28.09) forklarte de 935 seilasene uten AIS med at skipene var utenlandske: tilgangsbegrensning eller utdatert MMSI. 7 av 10 i en stikkprøve gir data i dag, med samme tilgang og samme MMSI. Forklaringen var en hypotese som hadde blitt stående som «sannsynliggjort» fordi den aldri ble testet mot API-et på nytt.
- **Hvordan det ble oppdaget:** som et sidefunn i stikkprøven til beslutning 09, der «empty»-seilaser var tatt med som kontrollgruppe.
- **Rettet i:** `bc97e76` (E0-S13).

## 2026-10-22 — Briefen hadde skjevheten snudd

- **Hva:** Risikopunktet i `brief.md` og `brief.no.md` sa at hullet i AIS-dataene ga en skjevhet «mot norskflagget trafikk». Det er motsatt: utenlandskflaggede skip mangler, så de er underrepresentert. Teksten har stått slik siden september.
- **Hvordan det ble oppdaget:** Da beslutning 07 ble skrevet om, ble det målt at 83 % av «empty»-seilasene er utenlandske, mot 33 % av dem med fasit.
- **Rettet i:** `bc97e76` (E0-S13).

## 2026-10-22 — Feil forventning i en review-rettelse (E1-S03)

- **Hva:** I review av E1-S03 fant Verification Gap-revieweren at `timer` aldri var testet med en annen verdi enn 24. Både revieweren og Claude (orkestratoren) skrev forventningen for `timer=6` som «12:00 inne, 14:00 ute» og begrunnet det med «12:00 < 06:00 + 6 t». Det er feil: vinduet er halvåpent, [06:00, 12:00), så 12:00 er *ute*.
- **Hvordan det ble oppdaget:** Implementasjons-subagenten skrev testen slik den var bedt om. Testen feilet mot koden. I stedet for å endre koden til å passe forventningen, sjekket den mot specen (halvåpent vindu), sa ifra og foreslo `timer=7` som alternativ.
- **Resultat:** Testen sjekker nå begge deler. `timer=6` gir `[1003, 1004]` (12:00 er ute), og `timer=7` gir `[1003, 1004, 1005, 1006]`. Mutasjonssjekk med kontrollkjøring på uendret kode: grønn på originalen. Testene feiler når `timer` er hardkodet til 24 t, når sluttgrensen er lukket (`<=`), og når fasit avgjøres av ankomsttid i stedet for status. Se commiten `git log --oneline --grep E1-S03`.
- **Lærdom (råt):**
  - To «uavhengige» KI-er gjorde samme regnefeil på grensen, så det at to er enige, er ikke en verifikasjon.
  - Det som fanget feilen, var at specen var tydelig på halvåpent vindu, og at en test som feiler ble behandlet som informasjon, ikke som noe som må gjøres grønt.

## 2026-10-27 — Arkitekturen motsa sin egen nye regel (E1-S04)

- **Hva:** Implementasjons-subagenten skrev den nye lekkasjeregelen i arkitektur §3: ingen prediktormodul får lese `data/utdrag/`. I samme seksjon lot den stå at «modellen leser tilstanden ved `t_H` fra `tilstand_ved_kutt.csv`», men den fila ligger i `data/utdrag/`. Dokumentet sa dermed to ting som ikke kan være sanne samtidig. E2-S07 ville ha bygd modellen slik teksten sa, og så feilet på AST-testen.
- **Hvordan det ble oppdaget:** Ingen av de tre reviewerne fant det. Claude (orkestratoren) så det under triagen, da den sjekket hvor `tilstand_ved_kutt.csv` ligger (`grep` i `docs/`) for å vurdere et funn om AIS etter kuttet.
- **Resultat:** §3 sier nå at tilstanden skal nå modellen gjennom grensen (`lag_input` eller en søsterfunksjon), og at nøyaktig hvordan avgjøres i E2-S07. Det er også ført i `deferred-work.md`. Se `git log --oneline --grep E1-S04`.
- **Lærdom (råt):** Tre reviewere leste diffen, men ingen sjekket påstandene i diffen mot resten av repoet. Selvmotsigelser mellom en ny regel og gammel tekst står ofte utenfor de endrede linjene.

## 2026-10-27 — En mutant som ikke kompilerte, så ut som en fanget mutant (E1-S04)

- **Hva:** I mutasjonssjekken la Claude til `faktisk_ankomst` med standardverdi *foran* `t_kutt` i `PrediksjonsInput`. Det gjør dataklassen ugyldig, så pytest stoppet med «2 errors» allerede ved innsamlingen. Det ser rødt ut, men ingen test hadde faktisk fanget lekkasjen.
- **Hvordan det ble oppdaget:** Claude la merke til at resultatet var «errors», ikke «failed», og kjørte mutanten på nytt med feltet sist og fylt fra `Anlop`. Da feilet fire lekkasjetester, slik de skal.
- **Lærdom (råt):** En mutant teller bare som fanget når en *test* feiler (failed). En importfeil eller syntaksfeil beviser ingenting om testene.

## 2026-10-27 — Story-ID brukt to ganger (E0-S05)

- **Hva:** Claude committet dagens promptlogg som `E0-S05` og skrev i sluttoppsummeringen at ingen story dekket loggen. E0-S05 var allerede brukt på planoppdateringen 16.10 (`2e7183d`). Da ville `git log --grep E0-S05` gitt to ulike arbeider, og det bryter regelen om at nummer aldri gjenbrukes.
- **Hvordan det ble oppdaget:** Gruppa så det i oppsummeringen. Claude hadde ikke sjekket `git log --all --grep` før den valgte ID-en, selv om tabellen i `docs/epics.md` viste at S05 var i bruk.
- **Resultat:** Commiten ble omdøpt til `E0-S16` før push (`68655d4`). E0-S16 er nå den faste ID-en for løpende logging, og E0-S17 brukes for omfangssjekken. Begge står i E0-tabellen.
- **Lærdom (råt):** Før en ID tas i bruk, sjekkes både tabellen og `git log --all --grep <ID>`. Det er billig.
