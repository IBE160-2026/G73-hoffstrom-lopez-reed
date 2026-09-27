# Kalibrert baseline med offset estimert kun på treningsdata

## Kontekst

Hovedetiketten (`arrival_in_area`, se beslutning 03) måler soneinngang ca. 15 km fra kai — en tidligere hendelse enn faktisk kaiankomst, som er det rapportert ETA trolig sikter mot. Rått avvik mellom soneinngang og ETA vil derfor systematisk se ut som "for tidlig", uavhengig av modellkvalitet.

## Alternativer vurdert

- **Bake korreksjonen inn i etiketten selv**, f.eks. `arrival_in_area + median(liggetid)` som en justert "kai-proxy".
- **La etiketten stå rå, kalibrer i stedet baseline-sammenligningen** (rapportert ETA).
- Innenfor sistnevnte: estimere offset på *hele* datasettet, eller kun på treningsdelen av en kronologisk splitt.

## Valg

Etiketten (`arrival_in_area`) forblir rå og ukalibrert. Baseline for sammenligning kalibreres i stedet: `kalibrert_baseline = rapportert_eta − offset`, der `offset = median(liggetid havneområde→kai)` beregnet **per ship_group** (rutegående/ikke-rutegående), og **kun på treningsdelen** av en kronologisk 80/20-splitt.

## Begrunnelse

Etiketten skal være en observasjon, ikke et estimat — å blande inn en median-korreksjon i selve fasiten gjør den til en modellert størrelse, og en fremtidig modell vil uansett lære en slik konstant forskyvning selv om den ikke er nødvendig i etiketten. Det er *baseline-sammenligningen* som trenger korreksjonen, ikke fasiten.

Offset må beregnes kun på treningsdata, aldri på hele datasettet — å inkludere testperioden ville lekke informasjon om nøyaktig den perioden vi evaluerer på, inn i selve målestokken. Splitten er kronologisk (ikke tilfeldig) fordi det er slik en reell modellevaluering uansett må gjøres, og fordi en tilfeldig splitt ville gitt en optimistisk, ikke-realistisk vurdering.

Offset beregnes per `ship_group` fordi rutegående og ikke-rutegående trafikk har markant ulik liggetid-fordeling (se addendum om skjevheten i selve liggetid-utvalget, beslutning 07-tilstøtende funn).

## Konsekvens

Rapportering må alltid vise både naiv og kalibrert baseline, begge evaluert på samme (test-)utvalg, med en forklarende setning om at forskjellen skyldes at de måler to ulike fysiske hendelser — ikke at kalibrert er en "bedre modell". Kalibreringstallet i seg selv er en støtte for å tolke baseline riktig, ikke et resultat å optimalisere isolert.
