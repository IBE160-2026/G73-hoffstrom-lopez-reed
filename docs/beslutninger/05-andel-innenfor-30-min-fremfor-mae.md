# ±30 min som hovedmetrikk fremfor MAE

## Kontekst

Vi trenger ett hovedtall for å rapportere hvor godt en prediksjon (eller, foreløpig, en kalibrert baseline) treffer faktisk ankomst. Første rapportering brukte MAE (gjennomsnittlig absolutt avvik) som hovedtall.

## Alternativer vurdert

- **MAE** (gjennomsnittlig absolutt avvik) som hovedmetrikk.
- **Median absolutt avvik** som hovedmetrikk.
- **Andel innenfor ±30 minutter** som hovedmetrikk, med presisjon/recall på et forsinkelsesflagg (>2 timer) som sekundær, og MAE/median som støttetall.

## Valg

Andel innenfor ±30 minutter som hovedmetrikk. Presisjon/recall på >2-timersflagget som sekundærmetrikk (når en modell finnes — se beslutning 06). MAE og median absolutt avvik beholdes, men kun som støttetall.

## Begrunnelse

MAE er ustabilt på en halefordelt fordeling. Ett konkret eksempel avdekket problemet: kalibrert baseline for ikke-rutegående trafikk viste median −6,6 minutter og 50 % av anløpene innenfor ±30 minutter — altså et flertall som treffer greit — mens MAE likevel lå på 365 minutter. Et fåtall ekstreme avvik dominerer gjennomsnittet fullstendig og gir et hovedtall som ikke gjenspeiler den typiske situasjonen en havnevakt faktisk opplever.

Andel innenfor ±30 minutter er robust mot nettopp dette: den svarer direkte på det operative spørsmålet ("kan jeg stole på dette anslaget i dag") uten at et fåtall ekstremtilfeller får dominere. Ekstremtilfellene mistes ikke — de fanges i stedet eksplisitt av forsinkelsesflagget og presisjon/recall (beslutning 06), som er nøyaktig det halen faktisk trenger å bli målt på.

## Konsekvens

All rapportering (konsoll-output i `derive_arrivals.py`, og senere brief/PRD) skal lede med ±30 min-andelen. MAE og median skal fortsatt beregnes og vises, men eksplisitt merket som støttetall, aldri som suksesskriteriet i seg selv.
