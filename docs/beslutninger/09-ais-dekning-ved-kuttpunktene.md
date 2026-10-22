# AIS-dekningen ved kuttpunktene: 24-timershorisonten beholdes

## Kontekst

Beslutning 08 målte at dagens AIS-cache har en posisjon like før kuttpunktet `t_24` for bare 7 % av Øvrige i testperioden, og 31 % ved `t_6`. Før modellfasen måtte vi vite hvorfor. Finnes posisjonene i Kystdatahuset i det hele tatt? Eller er skipene utenfor norsk AIS-rekkevidde 24 timer før ankomst? Er det siste tilfellet, må 24-timershorisonten droppes eller begrenses. Ingen stor henting skulle startes før spørsmålet var besvart.

## Hva vi undersøkte (22.10.2026)

Alt er gjort med `pipeline/sjekk_ais_dekning_kutt.py`, som er reproduserbart med fast seed. Hele undersøkelsen brukte rundt 120 API-kall.

1. **Hvor skipene kommer fra (uten nettkall).** 998 av 1 119 Øvrige-anløp i testperioden (89 %) har ETD mindre enn 24 t før ETA. Avgangshavnene er nesten bare norske: Karmøy, Ågotnes, Kleppestø, Sløvåg, Risavika og så videre. Ved `t_24` ligger altså de fleste skipene fortsatt i en norsk havn. Den lave cache-dekningen kommer av at hentevinduet i `fetch_ais.py` starter ved ETD (beslutning 02). Vi har aldri spurt om tiden før avgang.
2. **Stikkprøve mot API-et.** 40 tilfeldige Øvrige-anløp med fasit fra testperioden, der vi spurte om [`t_H` − 3 t, `t_H`]:

   | Horisont | Med posisjon | Avstand til Bergen, median | maks |
   |---|---|---|---|
   | 24 t | 25 / 40 | 165 km | 506 km |
   | 6 t | 28 / 40 | 87 km | 118 km |

   Posisjoner 500 km unna viser at arkivet dekker langt mer enn kystnære basestasjoner.
3. **De 15 uten posisjon ved `t_24`.** Vi spurte om de siste 24 timene før `t_24`:
   - 11 ble sist sett 3,6–18 t før `t_24` (median 5,8 t), med fart ≤ 2 knop, 1–190 km fra Bergen. Det er skip som ligger stille i eller ved en norsk havn. Arkivet har glisne punkter for skip som ligger i ro, så et vindu på 3 t treffer ikke.
   - 1 hadde posisjon rett ved `t_24`. Den manglet bare fordi API-et kuttet svaret, se funn B under.
   - 3 hadde ingen posisjon de siste 24 timene.

   Med 24 t tilbakeblikk har altså **37 av 40 (≈ 93 %) en posisjon ved `t_24`**. Utvalget er lite, så usikkerheten er omtrent ±8 prosentpoeng.

## Valg

- **24-timershorisonten beholdes.** Posisjonene finnes. At skipene skulle være utenfor rekkevidde, forklarer ikke hullet: de fleste ligger i en norsk havn.
- **Tilbakeblikket ved kuttpunktet utvides fra 3 t til 24 t:** [`t_H` − 24 t, `t_H`]. Alderen på posisjonen er allerede en input (beslutning 08), så modellen vet når en posisjon er gammel. «Lå fortsatt til kai for 6 t siden» er nyttig informasjon i seg selv. Kuttet er uendret: ingenting etter `t_H` brukes.
- **Hentingen i E2-S02 skal ta hensyn til tre egenskaper ved API-et (funn A–C).** Ellers lekker data etter `t_H` inn, eller det oppstår hull som ikke er ekte.

## Funn om API-et som gjelder alt videre AIS-arbeid

- **A — Ny adresse.** API-et har flyttet til `https://kystdatahuset.kystverket.no/ws/api/...`. Den gamle adressen svarer 301, og `urllib` følger ikke 301 på POST. `pipeline/fetch_ais.py` virker derfor ikke lenger uten endring.
- **B — Vinduet forskyves, og noen svar kuttes.** API-et returnerer posisjoner for et vindu som er forskjøvet +1 t (vintertid) eller +2 t (sommertid) i forhold til `start`/`end` i forespørselen. Tidsstemplene i svaret er likevel UTC. Det er kontrollert mot Hurtigrutens faste ankomst kl. 14:45 norsk tid: ETA er 13:45 UTC om vinteren og 12:45 UTC om sommeren, og AIS-sporet følger samme klokke. I tillegg ble svar på korte vinduer som slutter kort etter midnatt (sluttid 02:00 og 03:30 UTC i testen), kuttet ved 23:59:59 dagen før. Vinduer som slutter 06:00 eller senere, eller som er lengre enn ett døgn, ga fullstendige svar.
- **C — Konsekvens for henting.** Be alltid om et vindu med god margin på begge sider, for eksempel fra én dag før til én dag etter. Filtrer så på tidsstemplet i svaret. En forespørsel om [`t_H` − 3 t, `t_H`] uten filtrering gir punkter opptil 2 t *etter* `t_H`. Det er nøyaktig den lekkasjen FR9a forbyr. Filtreringen skal ha en egen test.

**Ankomstetikettene er ikke berørt.** De er regnet ut fra tidsstemplene i svaret, som er UTC, og ikke fra vinduet vi ba om. Tallene i FR8 (46,6 % / 79,6 %) står. Forskyvningen betyr bare at de opprinnelige hentevinduene startet 1–2 t senere enn tiltenkt.

## Ny åpen tråd: «empty»-seilasene

7 av 10 tilfeldige `empty`-seilaser fra testperioden, altså seilaser som ga null posisjoner i den opprinnelige hentingen, har i dag posisjoner i sitt opprinnelige hentevindu. Alle 7 har punkter innenfor 15 km fra Bergen. Beslutning 07 foreslo tilgangsbegrensning eller utdatert MMSI som forklaring, men det stemmer ikke for disse. Noe ved den opprinnelige hentingen ga tomme svar. Vi vet ikke hva, men funn B eller midlertidige tomme svar fra API-et er kandidater.

Vi henter **ikke** disse på nytt nå. Det ville endret det låste datasettet, regresjonstallene i FR8 og utdraget fra E1-S02. Om det skal gjøres, er et gruppevalg, og det står som åpent spørsmål i PRD §8. Opptil ~12 % av seilasene kan være mulig å berge.

## Konsekvens

- PRD FR9a: tilbakeblikket er nå 24 t, og kravet om filtrering på tidsstemplet i svaret er lagt til.
- Epics E2-S02 og E2-S03 og arkitektur §4 er oppdatert. E2-S02 bruker ny adresse, vindu med margin og filtrering, med test.
- Beslutning 08 står. Bare vinduet i konsekvensavsnittet er erstattet av denne beslutningen.
- Beslutning 07 bør revurderes når gruppa har tatt stilling til ny henting av `empty`.
