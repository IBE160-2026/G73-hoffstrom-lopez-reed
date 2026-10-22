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
