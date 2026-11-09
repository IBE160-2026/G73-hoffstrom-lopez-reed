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

## 2026-10-27 — Pipelinen rundet avviket før sammenligningen (12,9 % skulle vært 12,8 %)

- **Hva:** `pipeline/derive_arrivals.py:518`, skrevet med KI i september (co-author Claude Sonnet 5, `c1fe8c3`/`9299bbe`), runder avviket til 0,1 min før ±30 min-sammenligningen. Seilas 3542899 bommer med 30 min og 1 sekund. Den ble rundet til 30,0 og telt som treff. Naiv ETA for Øvrige ble dermed 12,9 % i stedet for 12,8 % (127/996). Tallet har stått i brief, PRD, addendum, UX, arkitektur, epics og beslutning 04 siden 28.09. 46,6 % og 79,6 % påvirkes ikke.
- **Hvordan det ble oppdaget:** Da regresjonstesten i E1-S05 ble spesifisert, *før* den var skrevet, regnet Claude tallene gjennom S04-kontrakten på det ekte utdraget for å sjekke at de låste tallene kunne reproduseres. 46,6 og 79,6 stemte, men naiv Øvrige ga 12,8. Claude sammenlignet den uavrundede tiden i utdraget med den avrundede kolonnen `deviation_in_area_minutes`, og nøyaktig én seilas skilte seg ut.
- **Resultat:** gruppa valgte å låse 12,8 % og rette dokumentene i bruk i E1-S05. Beslutning 04 og promptloggene står som historikk, med en merknad. Regelen fra E1-S02 om uavrundede tider gjelder overalt. Se `git log --oneline --grep E1-S05`.
- **Lærdom (råt):**
  - Et tall som har stått i sju dokumenter i en måned, var aldri regnet ut av en test.
  - Feilen ble funnet fordi tallene ble reprodusert *før* testen ble skrevet, og ikke skrevet inn i testen som fasit.
  - Avrunding i et mellomsteg er en kilde til avvik selv når sluttresultatet rundes til én desimal.

## 2026-10-27 — Samme testhull som i S03, gjentatt i S05 (fasit avgjort av ankomsttid, ikke status)

- **Hva:** Implementasjons-subagenten skrev `har_fasit()` riktig: status `ok` *og* utfylt ankomsttid. Testene den skrev, kunne likevel ikke skille dette fra en feil versjon som bare sjekker ankomsttiden. Testhjelperen satte alltid ankomsttid til `None` når status ikke var `ok`, så den feile versjonen passerte alle testene. Det er nøyaktig samme hull som review fant i E1-S03 22.10.
- **Hvordan det ble oppdaget:** Claudes egen mutasjonssjekk etter implementasjonen. Fem av seks mutanter ble fanget, og denne overlevde. Ingen av de tre reviewerne meldte den som et hull. Verification Gap-revieweren skrev tvert imot at den «ikke har noen realistisk regresjon», fordi datalaget setter ankomsttid til `None` i dag.
- **Resultat:** en ny test bygger et anløp med status `empty` *og* utfylt ankomsttid og viser at det holdes utenfor. Mutanten feiler nå. Se `git log --oneline --grep E1-S05`.
- **Lærdom (råt):**
  - Det at en regel holder i dag fordi et annet lag sørger for det, er ikke det samme som at testen låser regelen.
  - Lærdommen fra S03 ble ikke overført til S05 av seg selv. Mutasjonssjekken fanget det, ikke hukommelsen.

## 2026-10-27 — Avrundingsregelen ble bare brukt på ett skip i skissen (E0-S18)

- **Hva:** Gruppa bestemte at tider vises avrundet til nærmeste minutt. Claude rettet da UX-skissene, men bare BERGEN ENERGY (09:55 → 09:56), fordi det var eksempelet i spørsmålet. Alle Øvrige-anløp har offset 64,2 min, som gir :48 sekunder, så de rundes opp. Fem andre tider i skissen ble derfor stående feil: EINARSON, ELEKTRON, OCEAN RESPONSE, ELDJARN og SIEM PEARL. Commit-meldingen (`debbbf8`) sa at «UX-skissene er oppdatert».
- **Hvordan det ble oppdaget:** Da E1-S06 ble spesifisert, regnet Claude ut standardvinduet fra de ekte dataene og sammenlignet med skissen rad for rad.
- **Resultat:** De fem tidene rettes i E1-S06, med en linje i UX-endringsloggen. Se `git log --oneline --grep E1-S06`.
- **Lærdom (råt):** En regel ble brukt på eksempelet, ikke på mønsteret. Å regne ut alle radene fra data var billig, og det burde vært gjort da regelen ble innført.

## 2026-10-27 — Eksempelet på «tomt vindu» i UX-skissen hadde 7 anløp (E0-S02)

- **Hva:** UX §5 viste et tomt vindu som eksempel: «0 anløp · lør 01.11 03:00 – søn 02.11 03:00». Skissen ble skrevet av Claude i UI/UX-rollen 16.10 (`a1f0c5c`). Det vinduet har 7 anløp i dataene. Tidspunktet ble valgt fordi det så sannsynlig ut, men det ble aldri sjekket.
- **Hvordan det ble oppdaget:** Implementasjons-subagenten i E1-S06 trengte et vindu uten anløp for `test_tomt_vindu`, og prøvde eksempelet. Claude bekreftet det ved å telle på nytt (7 anløp 01.11 kl. 03:00, 0 anløp 03.02.2026 kl. 08:00).
- **Resultat:** UX §5 bruker nå tir 03.02.2026 08:00, som også er vinduet testen bruker. Endringen står i UX-endringsloggen. Se `git log --oneline --grep E1-S06`.
- **Lærdom (råt):** Et eksempel i en skisse er også en påstand om dataene. Det samme mønsteret ga feil skissetider i E0-S18.

## 2026-10-27 — Feilsøkingsråd i README skrevet uten å sjekke (E1-S16)

- **Hva:** I «Kom i gang» skrev Claude at port 5000 er «opptatt» på macOS fordi AirPlay bruker den, og at man må bytte port. Det var en antakelse fra generell kunnskap, og den ble ikke sjekket. I virkeligheten starter Flask fint på 127.0.0.1:5000. Det som går galt, er at `http://localhost:5000` havner hos AirPlay (403, `Server: AirTunes`) fordi `localhost` slås opp som `::1`.
- **Hvordan det ble oppdaget:** Gruppa ba om en tørrkjøring av README i en ny, tom mappe. Claude så at AirPlay lyttet på port 5000 mens Flask likevel svarte, og testet derfor `127.0.0.1`, `localhost` og `[::1]` hver for seg.
- **Resultat:** Rådet er skrevet om til det som faktisk skjer: bruk nøyaktig `127.0.0.1`, eller bytt port. Se `git log --oneline --grep E1-S16`.
- **Lærdom (råt):** Et feilsøkingsråd er en påstand om en feil. Skrives den uten at feilen er gjenskapt, kan den sende brukeren feil vei akkurat når de står fast.

## 2026-11-03 — Klone-testen ble grønn selv om `git clone` hadde feilet (E1-S16)

- **Hva:** I klone-testen fulgte Felipe README steg 1–4 mot `main`, og sluttresultatet var grønt: 179 tester grønne, appen svarte 200 på `http://127.0.0.1:8000`, og siden viste «15 anløp». Men steg 1 hadde feilet. `git clone` stoppet fordi mappa fantes fra et tidligere forsøk i samme økt, og testen fortsatte i den eksisterende mappa. Et grønt sluttresultat sa dermed ingenting om at README-ens første steg virket, eller om at koden som ble testet, var den på `main`.
- **Hvordan det ble oppdaget:** Vi leste hele terminalutskriften i stedet for bare sluttresultatet.
- **Resultat:** Det ble verifisert i etterkant at den eksisterende mappa var identisk med `main` (`59a5cbb`, «On branch main», up to date with origin/main). Testen er derfor gyldig, og avviket står i loggen (`.logs/felipe-knudstad-lopez/`).
- **Lærdom (råt):**
  - Samme mønster som tidsstempeltesten 22.10: et resultat som ser riktig ut, er ikke et bevis før man har sjekket hva som faktisk kjørte.
  - En klone-test må starte i en mappe som garantert ikke finnes fra før, ellers kan et feilet første steg skjules av en gammel kopi.
  - Les hele utskriften, ikke bare siste linje.

## 2026-11-03 — Røyktesten mot ekte data fant søppelposisjoner som alle fixture-testene hadde godkjent (E2-S03)

- **Hva:** `scripts/lag_tilstand.py` hadde 14 grønne tester og en mutasjonssjekk der alle mutasjonene ble fanget. Tre uavhengige reviewere hadde gått gjennom koden. Likevel ville utdraget ha fått rader med status `ok` og «siste posisjon» 7 000–17 000 km fra Bergen, 6 timer før ankomst. Alle seilasene det gjaldt, hadde MMSI 0, og API-et svarer da med posisjoner fra alle fartøy i verden som sender 0. 63 seilaser i datasettet har MMSI 0.
- **Hvordan det ble oppdaget:** Claude kjørte scriptet mot den delvise AIS-cachen. Cachen ble bare lest, og resultatet ble skrevet til scratchpad. Formålet var å sjekke kolonnerekkefølgen mot ekte API-punkter, etter at en reviewer hadde påpekt at testene og koden delte samme antakelse om kolonnene. Maksdistansen på 15 000 km falt ut i oppsummeringen, og alle de rare radene hadde MMSI 0.
- **Resultat:** Felipe bestemte at en posisjon er gyldig bare hvis MMSI-en i punktet er lik seilasens MMSI og har 9 sifre. Regelen har en egen test og er mutasjonssjekket. Etter endringen er maksdistansen 645 km ved 24 t. Funnet står i beslutning 07: 63 av de 935 tomme seilasene, og hva det ikke forklarer. Se `git log --oneline --grep E2-S03`.
- **Lærdom (råt):**
  - Fixtures tester det vi tenkte på. Ekte data inneholder det vi ikke tenkte på.
  - Alle testene og mutasjonene var grønne fordi ingen fixture hadde et punkt som tilhørte et annet fartøy.
  - En mutasjonssjekk viser at testene fanger feil i koden, ikke at koden dekker dataene.
  - Kjør på ekte data før commit, og se på ytterpunktene (min og maks), ikke bare medianen.


## 2026-11-05 — Stoppregelen tolket et permanent datahull som et API-brudd, og hentingen sto stille i nesten to døgn (E2-S02)

- **Hva:** Fullkjøringen av `pipeline/fetch_ais_kutt.py` stoppet 03.11 kl. 19:42 etter 2 185 av 7 826 seilaser. Utskriften sa «API-et er trolig nede». Det var feil. De ti siste feilene var alle `42P01: relation "ais202407.ais_20240730" does not exist`: dagstabellen for 30.07.2024 mangler hos Kystdatahuset. Seilasene hentes i tidsrekkefølge, så ti seilaser på rad hadde vinduer over den samme dagen, og stoppregelen («10 feil på rad») slo til. Scriptet ble skrevet med Claude i E2-S02 (`85021b9`). Der var 42P01 allerede sett i piloten og merket som varig, så det ikke ble prøvd på nytt, men det talte likevel mot stoppregelen. I tillegg ga hver slik feil opp hele seilasen, selv om bare én av fire dager i vinduet manglet.
- **Hvordan det ble oppdaget:** Felipe leste kjøreloggen 05.11, nesten to døgn senere. I mellomtiden hadde ingen sett at hentingen sto stille.
- **Resultat:** `0a85cd4`. 42P01 teller ikke lenger mot stoppregelen. Vinduet deles rundt den manglende dagen, og resten hentes. Prøvekall 05.11 viste at API-et velger dagstabeller etter datoen i forespørselen, og delvinduene forlenges til minst 25 t på grunn av midnattskuttet (funn B). De manglende dagene lagres i cachen og telles i `ais_kutt_dekning.csv`. Alle de 11 seilasene som hadde feilet med 42P01, er hentet på nytt uten feil (9 `ok`, 2 `tom`), og fullkjøringen ble startet igjen 05.11 kl. 14:17.
- **Lærdom (råt):**
  - Sjekk loggen til en lang kjøring samme kveld eller neste morgen. En stoppet jobb er stille.
  - En stoppregel må skille mellom «API-et svarer ikke» og «API-et svarer at dataene ikke finnes». Det siste er et permanent datahull, ikke et brudd.
  - Feilen var kjent fra piloten, men ble bare håndtert ett sted (ikke nytt forsøk) og ikke tenkt gjennom for stoppregelen. Et kjent spesialtilfelle må følges gjennom alle steder det påvirker.
  - Meldingen «API-et er trolig nede» var en påstand scriptet ikke hadde grunnlag for, og den kunne fått oss til å vente i stedet for å se etter.

## 2026-11-06 — To tester var lovet i specene, men fantes ikke (E2-S03, E2-S04)

- **Hva:** E2-S03-specen lovet `test_committet_tilstand`, og E2-S04-specen lovet `test_committet_features`. Begge sto som oppgaver «etter hentingen», og E2-S03 sto til og med som `status: 'done'`. Ingen av testene fantes. Hadde utdragene blitt committet uten dem, ville ingenting ha låst radantall, sha256 eller grensen på 10 MB. Det er andre gang mønsteret oppstår: tidsstempeltesten 22.10 var «spesifisert, men aldri implementert» på samme måte.
- **Hvordan det ble oppdaget:** etter `lag_tilstand.py` søkte Claude etter `def test_committet` i `tests/` og fikk ingen treff. Deretter leste Claude oppgavene i specene, der testene sto beskrevet.
- **Resultat:** begge testene ble skrevet og committet sammen med utdragene: `910028c` og `47a2c02`.
- **Lærdom (råt):**
  - At en test står i specen, er ikke det samme som at den finnes. Sjekk at en lovet test finnes med `pytest --collect-only` eller grep i `tests/`, ikke ved å lese specen.
  - En spec kan stå som `done` med åpne oppgaver. Sjekk avkrysningene, ikke statusfeltet.
  - Lærdommen fra 22.10 ble ikke overført av seg selv. Den må inn som et fast steg når en story settes til ✅.

## 2026-11-06 — Review-funnet hadde feil forventet antall kall (E2-S02)

- **Hva:** I review av `0a85cd4` (05.11) sto det at en test der samme dag alltid kommer igjen, skulle gi «exactly 3 calls». Det riktige er 2: hele vinduet, og så første delvindu, som gir samme dag igjen, og da gir koden opp. Claude skrev i tillegg selv feil forventning, 3 kall, i `test_maks_delinger`. Det riktige var 5, fordi delvinduene til venstre lykkes mellom delingene.
- **Hvordan det ble oppdaget:** testene feilet mot koden, og kallene ble talt opp for hånd.
- **Resultat:** `8694a48`. Begge forventningene er rettet, med en kommentar som viser kallene. Avviket fra review-funnet er ført i E2-S02-specen.
- **Lærdom (råt):** Et tall i et review-funn er en påstand, ikke en fasit. Samme mønster som «Feil forventning i en review-rettelse» 22.10. Spor kallene for hånd før forventningen skrives inn.

## 2026-11-09 — Fem testhull i treningsskriptet, og commits med feil forfatter (E2-S05)

- **Hva:** implementeringssubagenten skrev `scripts/tren.py` med 8 grønne tester og meldte at mutasjonssjekken var gjort. Verification Gap-revieweren fant likevel fem endringer som ingen test fanget:
  - fortegnet på målet snudd, og offseten lagt til i stedet for trukket fra
  - valgregelen sortert på MAE først
  - historikken i modellvalget slått av, som ville lekket valideringshistorikk inn i valget
  - treffgrensen endret fra 30 til 60 min
  - ingen sjekk av de committede artefaktene

  I tillegg committet subagenten med Theodor som forfatter, selv om økta skulle ha Felipe.
- **Hvordan det ble oppdaget:** reviewen etter implementeringen, med tre lag i parallell, og Claude som kontrollerte `git log` før push.
- **Resultat:** `36eebb0` har fem nye tester, og artefaktene har fått offset og sha for baseline. Forfatteren ble skrevet om med rebase før push.
- **Lærdom (råt):**
  - Testene sjekket at to kjøringer ga samme resultat og at strukturen stemte, men ikke at verdiene var riktige. Et program kan være feil på samme måte to ganger.
  - Mutasjonssjekken dekket filtrene implementeringen selv tenkte på, ikke målet eller metrikken.
  - En subagent vet ikke om forfatterregelen i økta. Sjekk `git log --format='%an'` før push.


## 2026-11-09 — Specen ba om valideringstall målt på treningsrader, og varselstreken ble senket uten at det sto noe sted (E2-S06)

- **Hva:**
  - Claude skrev E2-S06-specen slik at valideringsdelen skulle evalueres med de endelige artefaktene. De er trent på trening + validering, så modelltallene ble målt på rader modellen hadde sett. Modellutvalget viste 78,2 % og 72,4 % innenfor ±30 min, mot 69,1 % og 59,8 % holdt ut.
  - Da bestått/ikke bestått ble flyttet til modellutvalget, fulgte varselstreken med. «Varsle alle» gikk fra F1 0,33 til 0,14 og 0,19, fordi 137 av 194 forsinkede anløp (6 t) ligger utenfor utvalget. Det skjedde etter at valideringstallene var kjent, men verken specen eller endringsloggene sa det.
  - Subagenten committet igjen med Theodor som forfatter.
- **Hvordan det ble oppdaget:** implementeringssubagenten meldte at tallene var målt på treningsrader og la inn en merknad. Blind Hunter fant varselstreken. Claude sjekket `git log` før review.
- **Resultat:** Felipe valgte at validering skal bruke en modell trent på nytt i minnet, bare på treningsdelen (beslutning 4), og at briefen og PRD skal si rett ut at varselstreken er lavere, hvorfor, og når den ble flyttet (beslutning 5). Rettet i `d36964c` og `78a6a02`. Tallene på validering er nå lik `modellvalg.json`, og en test låser det.
- **Lærdom (råt):**
  - Et artefakt som er trent på hele treningsperioden, kan ikke brukes til å evaluere en del av den. Det burde vært sett da specen ble skrevet, fordi `tren.py` sier rett ut at den endelige modellen trenes på begge delene.
  - Når et kriterium flyttes, flytter alle delene av det seg. Sjekk hver strek for seg, både for ±30 og for varsel, og skriv det ned hvis en strek blir lettere.
  - Forfatterfeilen skjedde for andre gang. Det må stå i oppdraget til subagenten, ikke bare sjekkes etterpå.
