"""Featurene F1–F16 ved kuttpunktet (E2-S04, beslutning 11, PRD FR9a).

Bare rene funksjoner: modulen leser ingen filer og importerer ikke datalaget. AST-regelen i
``tests/test_prediktor_kontrakt.py`` gjelder også for den. Data lastes av
``scripts/lag_features.py`` (trening og featurefila) eller gjennom grensen i ``__init__.py`` (E2-S07).

Fartøyhistorikken (F15–F16) bygges av ``Historikk``. Den tar bare imot treningsrader med fasit og
gyldig MMSI, og svarer bare med aggregater for anløp med ankomst før ``t_kutt``. Raden selv er
aldri med.
"""
import bisect
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")
PORT_LAT, PORT_LON = 60.398, 5.321      # samme referansepunkt som pipeline og tilstandsfila (E2-S03)
SONE_KM = 15.0                          # ankomstsonen (beslutning 03)
KM_PER_NM = 1.852
MIN_FART_KN = 1.0
FART_IKKE_TILGJENGELIG = 102.3          # AIS-verdien for «ikke tilgjengelig»
ETD_MAKS_FOR_ETA = timedelta(days=14)   # samme sanitetsgrense som pipeline/fetch_ais.py (beslutning 02)
SLAKK_MIN_TIMER = -48.0
SHRINK_K = 5
SJELDEN_TERSKEL = 20
TRENINGSANDEL = 0.8                     # samme trunkering som E1-S02: int(n * 0.8)
ANNET = "annet"


# ---------- F1–F7: tilstand ved kuttet ----------

def peiling_grader(lat: float, lon: float, lat2: float = PORT_LAT, lon2: float = PORT_LON) -> float:
    """Startpeiling (0–360°) fra posisjonen til havna."""
    p1, p2 = math.radians(lat), math.radians(lat2)
    dl = math.radians(lon2 - lon)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _gyldig_fart(fart: Optional[float]) -> bool:
    return fart is not None and math.isfinite(fart) and 0 <= fart < FART_IKKE_TILGJENGELIG


def _endelig(*verdier) -> bool:
    return all(v is not None and math.isfinite(v) for v in verdier)


def kurs_mot_havn(lat: Optional[float], lon: Optional[float], kurs: Optional[float],
                  fart: Optional[float], distanse_km: Optional[float]) -> Optional[float]:
    """F3: cos(kurs − peiling til havna). Tom ved manglende/ugyldig kurs, fart < 1 kn eller distanse 0."""
    if not _endelig(lat, lon, kurs, distanse_km) or not _gyldig_fart(fart):
        return None
    if not (0 <= kurs < 360) or fart < MIN_FART_KN or distanse_km <= 0:
        return None
    return math.cos(math.radians(kurs - peiling_grader(lat, lon)))


def i_sonen(distanse_km: Optional[float]) -> Optional[int]:
    """F6: posisjonen ved kuttet er innenfor ankomstsonen. Regnet fra posisjonen, aldri fra fasit."""
    if not _endelig(distanse_km):
        return None
    return int(distanse_km <= SONE_KM)


def slakk_timer(distanse_km: Optional[float], fart: Optional[float], h_eff: float) -> Optional[float]:
    """F7: H_eff − (distanse i nm) / max(fart, 1 kn), klippet til [−48, H_eff]. Tom uten gyldig fart
    (også ved 102,3 kn og NaN, selv om tilstandsfila alt har tømt dem)."""
    if not _endelig(distanse_km) or not _gyldig_fart(fart):
        return None
    if distanse_km <= 0:
        return h_eff
    verdi = h_eff - (distanse_km / KM_PER_NM) / max(fart, MIN_FART_KN)
    return min(max(verdi, SLAKK_MIN_TIMER), h_eff)


# ---------- F8–F14: skip, kalender og seilas ----------

def kalender(eta_utc: datetime) -> Dict[str, float]:
    """F10–F12 fra rapportert ETA i norsk tid. ``eta_utc`` er naiv UTC eller tz-aware."""
    if eta_utc.tzinfo is None:
        eta_utc = eta_utc.replace(tzinfo=timezone.utc)
    lokal = eta_utc.astimezone(OSLO)
    time = lokal.hour + lokal.minute / 60
    return {
        "eta_time_sin": math.sin(2 * math.pi * time / 24),
        "eta_time_cos": math.cos(2 * math.pi * time / 24),
        "eta_ukedag": lokal.weekday(),
        "eta_maned_sin": math.sin(2 * math.pi * (lokal.month - 1) / 12),
        "eta_maned_cos": math.cos(2 * math.pi * (lokal.month - 1) / 12),
    }


def gyldig_etd(etd: Optional[datetime], eta: datetime) -> Optional[datetime]:
    """ETD mer enn 14 døgn før ETA (for eksempel plassholderen 0001-01-01) regnes som manglende."""
    if etd is None or etd < eta - ETD_MAKS_FOR_ETA:
        return None
    return etd


def avgang(etd: Optional[datetime], t_kutt: datetime) -> Tuple[Optional[int], Optional[float]]:
    """F14: (avgått før kuttet, timer siden avgang). Ligger ETD etter kuttet, gir det (0, None): bare
    *at* skipet ikke har gått, brukes, aldri selve ETD-verdien."""
    if etd is None:
        return None, None
    if etd <= t_kutt:
        return 1, (t_kutt - etd).total_seconds() / 3600
    return 0, None


def lengde(verdi) -> Optional[float]:
    """F9: lengde i meter, tom hvis den mangler eller ikke er positiv."""
    try:
        v = float(verdi)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def lag_kategorikart(verdier_fit: Iterable[Optional[str]], terskel: int = SJELDEN_TERSKEL) -> frozenset:
    """Kategoriene med minst ``terskel`` forekomster i fitdataene. E2-S05 kaller den på Øvrige-rader i
    dataene modellen fittes på, aldri på testperioden."""
    teller: Dict[str, int] = {}
    for v in verdier_fit:
        if v:
            teller[v] = teller.get(v, 0) + 1
    return frozenset(k for k, n in teller.items() if n >= terskel)


def grupper_sjeldne(verdi: Optional[str], kart: frozenset) -> str:
    """F8/F13: verdien hvis den er i kartet, ellers ``annet``. Det gjelder også manglende og ukjente verdier."""
    return verdi if verdi and verdi in kart else ANNET


# ---------- F15–F16: fartøyhistorikk, bare fra treningsdata ----------

@dataclass(frozen=True)
class Historikkrad:
    """Ett treningsanløp med fasit. Lages bare av ``scripts/lag_features.py`` fra train-splitten."""
    voyageid: str
    mmsino: str
    ovrige: bool
    ankomst: datetime          # arrival_in_area, naiv UTC
    avvik_min: float           # ankomst − (rapportert ETA − offset[gruppe])


def gyldig_mmsi(mmsi) -> bool:
    m = str(mmsi).strip()
    return len(m) == 9 and m.isdigit()


class _Rekke:
    """Sorterte ankomster med kumulative summer, så snitt før et tidspunkt er O(log n)."""

    def __init__(self, rader: List[Historikkrad]):
        rader = sorted(rader, key=lambda r: (r.ankomst, r.voyageid))
        self.tider = [r.ankomst for r in rader]
        self.ider = {r.voyageid: r for r in rader}
        self.sum = [0.0]
        for r in rader:
            self.sum.append(self.sum[-1] + r.avvik_min)

    def foer(self, t: datetime, unntatt: Optional[str]) -> Tuple[int, float]:
        i = bisect.bisect_left(self.tider, t)          # ankomst strengt før t
        n, s = i, self.sum[i]
        egen = self.ider.get(unntatt) if unntatt is not None else None
        if egen is not None and egen.ankomst < t:
            n, s = n - 1, s - egen.avvik_min
        return n, s


class Historikk:
    """F15–F16. Bygges bare av treningsrader med fasit og gyldig MMSI."""

    def __init__(self, treningsrader: Sequence[Historikkrad]):
        rader = [r for r in treningsrader if gyldig_mmsi(r.mmsino)]
        self._ovrige = _Rekke([r for r in rader if r.ovrige])
        per: Dict[str, List[Historikkrad]] = {}
        for r in rader:
            per.setdefault(r.mmsino, []).append(r)
        self._fartoy = {m: _Rekke(rs) for m, rs in per.items()}

    def maal(self, t_kutt: datetime, voyageid: Optional[str] = None) -> float:
        """Snittet for Øvrige som F15 trekkes mot: treningsrader med ankomst før ``t_kutt``. 0 uten slike."""
        n, s = self._ovrige.foer(t_kutt, voyageid)
        return s / n if n else 0.0

    def fartoy(self, mmsino: str, t_kutt: datetime, voyageid: Optional[str] = None) -> Tuple[float, int]:
        """(F15, F16) for fartøyet ved ``t_kutt``, trukket mot ``maal`` med k = 5."""
        maal = self.maal(t_kutt, voyageid)
        rekke = self._fartoy.get(str(mmsino)) if gyldig_mmsi(mmsino) else None
        if rekke is None:
            return maal, 0
        n, s = rekke.foer(t_kutt, voyageid)
        if n == 0:
            return maal, 0
        return (s + SHRINK_K * maal) / (n + SHRINK_K), n


# ---------- Valideringssplitt ----------

def valideringssplitt(rader: Sequence[dict]) -> Dict[str, str]:
    """voyageid → ``trening``/``validering``/``test``. Treningsrader sorteres stabilt på
    ``eta_reported`` (strengen, som i E1-S02), og de siste 20 % blir validering."""
    trening = sorted((r for r in rader if r["split"] == "train"), key=lambda r: r["eta_reported"])
    grense = int(len(trening) * TRENINGSANDEL)
    deler = {r["voyageid"]: "test" for r in rader if r["split"] == "test"}
    for i, r in enumerate(trening):
        deler[r["voyageid"]] = "trening" if i < grense else "validering"
    return deler
