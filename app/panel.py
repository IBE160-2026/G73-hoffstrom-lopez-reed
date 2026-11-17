"""Panelet «modell mot baseline» på hovedskjermen (E2-S09, PRD FR10, UX §2).

Modulen leser bare ``data/modell/metrikker.json`` (stien er ``app.prediksjon.METRIKKER_FIL``) og, etter
testkjøringen, ``konfidensintervall.json`` i samme mappe, og former tallene for malen. Den regner ingenting fra
utdrag eller prediksjoner. Hvert tall på skjermen er en verdi fra filene, bare avrundet for visning. Unntakene er
differansen modell − baseline i prosentpoeng og dommen, som sammenligner verdier fra filene.

- Før testkjøringen (``testkjoringer() < 1``, samme funksjon som låsen) vises ``validering``-blokken, uten dom.
- Etter testkjøringen vises ``test``-blokken, med dom per horisont på modellutvalget:
  - ±30 min (E2-S11, PRD FR10): «bestått» bare når nedre grense i 95 % KI for differansen er over marginen i
    ``konfidensintervall.json`` (3 pp), ellers «ikke påvist». Mangler fila, eller passer den ikke med
    ``metrikker.json`` (annen n eller differanse), står «kan ikke avgjøres».
  - Varsel-F1: «bestått» når modellens F1 er over «varsle alle», ellers «ikke bestått». Ingen margin.
- ``test_bare_baseline`` og ablasjonen (``ablasjon_uten_f13_f14``) vises aldri her.
- Mangler fila eller blokken, eller har blokken feil form, sier panelet «Tall mangler».
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import app.prediksjon as prediksjon

HORISONTER = (("6", "6 t"), ("24", "24 t"))
PERIODE_VALIDERING = "Validering (mai–sep 2025) — utviklingstall, ikke testresultat"
PERIODE_TEST = "Testperioden (14.09.2025–15.03.2026)"
KAN_IKKE_VARSLE = "kan ikke varsle"
MODELL, BASELINE, VARSLE_ALLE = "Modell", "Baseline", "«Varsle alle»"
KI_FILNAVN = "konfidensintervall.json"
BESTATT, IKKE_PAVIST, IKKE_BESTATT, KAN_IKKE_AVGJORES = "bestått", "ikke påvist", "ikke bestått", "kan ikke avgjøres"


def _endelig(x, hva: str) -> float:
    """Et endelig tall fra fila. bool, tekst, NaN og ±uendelig gir TypeError, så panelet sier «Tall mangler»."""
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise TypeError(f"{hva} må være et endelig tall, ikke {x!r}")
    return x


def _pst(x) -> str:
    """Andel som prosent med én desimal og desimalkomma: 0.690632 → «69,1 %»."""
    return f"{_endelig(x, 'andel') * 100:.1f}".replace(".", ",") + "\u00a0%"


def _heltall(n) -> str:
    """Antall med hardt mellomrom som tusenskille: 1252 → «1 252»."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"antall må være et heltall, ikke {n!r}")
    return f"{n:,}".replace(",", "\u00a0")


def _brok(teller, nevner) -> str:
    return f"{_heltall(teller)}/{_heltall(nevner)}"


def _andel_med_antall(andel, teller, nevner) -> str:
    return f"{_pst(andel)} ({_brok(teller, nevner)})"


def _f1(x, desimaler: int = 2) -> str:
    if x is None:
        return KAN_IKKE_VARSLE
    return f"{_endelig(x, 'F1'):.{desimaler}f}".replace(".", ",")


def _celle(deler, arm: str) -> dict:
    """``deler`` er tekstbiter; et tall (andel eller antall) står alltid samlet i én bit (``tall = True``)."""
    deler = [d if isinstance(d, dict) else {"tekst": d, "tall": False} for d in deler]
    return {"tekst": " ".join(d["tekst"] for d in deler), "deler": deler, "arm": arm, "ikke_aktuelt": False}


def _tall(tekst: str) -> dict:
    return {"tekst": tekst, "tall": True}


def _andel_celle(andel, teller, nevner, arm: str) -> dict:
    return _celle([_tall(_pst(andel)), _tall(f"({_brok(teller, nevner)})")], arm)


def _ikke_aktuelt(arm: str) -> dict:
    return {"tekst": "–", "deler": [], "arm": arm, "ikke_aktuelt": True}


def _treff30(arm: dict, navn: str) -> dict:
    return _andel_celle(arm["andel_30"], arm["treff_30"], arm["n"], navn)


def _brokandel(andel, teller, nevner, ingen: str, arm: str) -> dict:
    """Presisjon eller recall. ``null`` er «kan ikke varsle», aldri 0. Er nevneren 0, er andelen ikke definert,
    og cellen sier hvorfor («ingen varsler (0/0)») i stedet for «0,0 %»."""
    if andel is None:
        return _celle([KAN_IKKE_VARSLE], arm)
    if _endelig(nevner, "antall") == 0:
        return _celle([ingen, _tall(f"({_brok(teller, nevner)})")], arm)
    return _andel_celle(andel, teller, nevner, arm)


def _varselceller(v: dict, navn: str):
    """Presisjon (treff/varsler), recall (treff/forsinket) og F1."""
    presisjon = _brokandel(v["presisjon"], v["treff"], v["varsler"], "ingen varsler", navn)
    recall = _brokandel(v["recall"], v["treff"], v["forsinket"], "ingen forsinkede", navn)
    f1 = _celle([KAN_IKKE_VARSLE] if v["f1"] is None else [_tall(_f1(v["f1"]))], navn)
    return presisjon, recall, f1


def _sammenlign(a, b, skala: float, desimaler: int, enhet: str, subjekt: str = "modellen") -> str:
    """a − b med fortegn og ord, så et tap står like tydelig som en seier. Ordet velges fra den uavrundede
    differansen: «likt» bare når verdiene er like. Runder differansen til 0, står det «<0,1» (eller «<0,01»)."""
    d = (_endelig(a, "verdi") - _endelig(b, "verdi")) * skala
    if d == 0:
        return f"±{0:.{desimaler}f}{enhet} (likt)".replace(".", ",")
    tall = f"{abs(d):.{desimaler}f}"
    if float(tall) == 0:
        tall = "<" + f"{10 ** -desimaler:.{desimaler}f}"
    else:
        tall = ("+" if d > 0 else "−") + tall
    ord_ = f"{subjekt} bedre" if d > 0 else f"{subjekt} dårligere"
    return f"{tall}{enhet} ({ord_})".replace(".", ",")


def _differanse(modell: dict, baseline: dict, subjekt: str = "modellen") -> str:
    """Modell − baseline, innenfor ±30 min, i prosentpoeng."""
    return _sammenlign(modell["andel_30"], baseline["andel_30"], 100, 1, " pp", subjekt)


def _differanse_f1(modell: dict, varsle_alle: dict, subjekt: str = "modellen") -> str:
    """Modell − «varsle alle», varsel-F1. Er en av dem ``null``, kan de ikke sammenlignes."""
    f1_modell, f1_alle = modell["varsel"]["f1"], varsle_alle["f1"]
    if f1_modell is None or f1_alle is None:
        return "kan ikke sammenlignes"
    return _sammenlign(f1_modell, f1_alle, 1, 2, "", subjekt)


def _pp(x) -> str:
    """Andel som prosentpoeng med én desimal, desimalkomma og ekte minus: −0.020 → «−2,0»."""
    return f"{_endelig(x, 'andel') * 100:.1f}".replace(".", ",").replace("-", "−")


def les_ki(sti: Optional[Path]) -> Optional[dict]:
    """``konfidensintervall.json`` som dict, eller ``None`` når fila mangler eller ikke kan leses."""
    try:
        return json.loads(Path(sti).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _ki_treff(ki: Optional[dict], h: str, modell: dict, baseline: dict):
    """(differanse, nedre, øvre, margin) for horisonten, eller ``None`` hvis intervallet mangler eller ikke passer
    med ``metrikker.json``: samme n, og samme differanse modell − baseline (til 6 desimaler, som i filene)."""
    try:
        v = ki["horisonter"][h]
        t = v["treff_30"]
        nedre, ovre = (_endelig(x, "KI-grense") for x in t["bootstrap"])
        margin = _endelig(ki["margin"], "margin")
        d = _endelig(t["differanse"], "differanse")
        if v["n"] != modell["n"] or v["n"] != baseline["n"]:
            return None
        if abs(d - (modell["andel_30"] - baseline["andel_30"])) > 2e-6:
            return None
        return d, nedre, ovre, margin
    except (KeyError, TypeError, ValueError):
        return None


def dom_treff(nedre: float, margin: float) -> str:
    """±30 min (E2-S11): bestått bare når nedre grense i 95 % KI er over marginen. Ellers «ikke påvist»."""
    return BESTATT if nedre > margin else IKKE_PAVIST


def _dom(modell: dict, baseline: dict, varsle_alle: dict, ki: Optional[dict] = None, h: str = "") -> list:
    """Dommen på modellutvalget (FR10). ±30 min avgjøres av konfidensintervallet (``dom_treff``), varsel-F1 av
    F1 over «varsle alle». F1 vises med tre desimaler i dommen. Er F1 for «varsle alle» ``null``, kan F1-dommen
    ikke avgjøres."""
    andeler = f"modell {_pst(modell['andel_30'])}, baseline {_pst(baseline['andel_30'])}"
    treff = _ki_treff(ki, h, modell, baseline)
    if treff is None:
        linje_treff = f"Innenfor ±30 min: {KAN_IKKE_AVGJORES} ({andeler}; konfidensintervallet mangler eller passer ikke)"
    else:
        d, nedre, ovre, margin = treff
        linje_treff = (f"Innenfor ±30 min: {dom_treff(nedre, margin)} ({andeler}; "
                       f"{'+' if d >= 0 else ''}{_pp(d)} pp, 95 % KI [{_pp(nedre)}; {_pp(ovre)}], "
                       f"krav: nedre grense over {_pp(margin)} pp)")
    f1_modell, f1_alle = modell["varsel"]["f1"], varsle_alle["f1"]
    if f1_alle is None:
        f1_dom = KAN_IKKE_AVGJORES
    else:
        f1_dom = BESTATT if f1_modell is not None and f1_modell > f1_alle else IKKE_BESTATT
    return [linje_treff, f"Varsel-F1: {f1_dom} (modell {_f1(f1_modell, 3)}, «varsle alle» {_f1(f1_alle, 3)})"]


# All Øvrige-trafikk: modellarmen er modellen pluss baselinen for anløpene modellen ikke brukes på, så raden
# viser «systemet», ikke «modellen» (Felipe, 11.11.2026).
SYSTEM = "Systemet"
FORKLARING_ALLE = ("De fleste forsinkelsene i all trafikk er turer inne i havneområdet, der modellen ikke brukes og "
                   "baselinen ikke kan varsle. Modellutvalget er raden som viser modellen.")


def _ovrige_gruppe(navn: str, blokk: dict, med_dom: bool, system: bool = False, ki: Optional[dict] = None,
                   h: str = "") -> dict:
    modell, baseline, alle = blokk["modell"], blokk["baseline"], blokk["varsle_alle"]
    arm = SYSTEM if system else MODELL
    subjekt = "systemet" if system else "modellen"
    p_m, r_m, f_m = _varselceller(modell["varsel"], arm)
    p_b, r_b, f_b = _varselceller(baseline["varsel"], BASELINE)
    p_a, r_a, f_a = _varselceller(alle, VARSLE_ALLE)
    return {
        "navn": navn,
        "kolonner": [arm, BASELINE, VARSLE_ALLE],
        "arm": arm,
        "forklaring": FORKLARING_ALLE if system else None,
        "rader": [
            {"maal": "Innenfor ±30 min", "celler": [_treff30(modell, arm), _treff30(baseline, BASELINE),
                                                    _ikke_aktuelt(VARSLE_ALLE)]},
            {"maal": "Presisjon", "celler": [p_m, p_b, p_a]},
            {"maal": "Recall", "celler": [r_m, r_b, r_a]},
            {"maal": "F1", "celler": [f_m, f_b, f_a]},
        ],
        "differanse": _differanse(modell, baseline, subjekt),
        "differanse_f1": _differanse_f1(modell, alle, subjekt),
        "dom": _dom(modell, baseline, alle, ki, h) if med_dom else None,
    }


def _passasjer_gruppe(blokk: dict) -> dict:
    baseline = blokk["baseline"]
    p, r, f = _varselceller(baseline["varsel"], BASELINE)
    return {
        "navn": "Passasjer (rutegående, bare baseline)",
        "kolonner": [BASELINE],
        "rader": [
            {"maal": "Innenfor ±30 min", "celler": [_treff30(baseline, BASELINE)]},
            {"maal": "Presisjon", "celler": [p]},
            {"maal": "Recall", "celler": [r]},
            {"maal": "F1", "celler": [f]},
        ],
        "arm": None,
        "forklaring": None,
        "differanse": None,
        "differanse_f1": None,
        "dom": None,
    }


def _horisont(etikett: str, h: dict, med_dom: bool, ki: Optional[dict] = None, nokkel: str = "") -> dict:
    ovrige, passasjer = h["antall"]["ovrige"], h["antall"]["passasjer"]
    return {
        "etikett": etikett,
        "fasit_ovrige": f"{_heltall(ovrige['med_fasit'])} av {_heltall(ovrige['rader'])}",
        "fasit_passasjer": f"{_heltall(passasjer['med_fasit'])} av {_heltall(passasjer['rader'])}",
        "modellandel": _andel_med_antall(h["andel_modellutvalg"]["med_fasit"],
                                         ovrige["modellutvalg_med_fasit"], ovrige["med_fasit"]),
        "grupper": [
            _ovrige_gruppe("Øvrige, modellutvalget", h["ovrige_modellutvalg"], med_dom, ki=ki, h=nokkel),
            _ovrige_gruppe("Øvrige, alle (resten får baseline)", h["ovrige_alle"], False, system=True),
            _passasjer_gruppe(h["passasjer"]),
        ],
    }


def lag_panel(sti: Optional[Path] = None, ki_sti: Optional[Path] = None) -> dict:
    """Panelets innhold fra ``metrikker.json`` og, etter testkjøringen, ``konfidensintervall.json`` (standard: i
    samme mappe). Kaster aldri: feil fil eller form gir ``mangler = True``. Mangler bare intervallfila, vises
    tallene, og ±30 min-dommen sier «kan ikke avgjøres»."""
    sti = prediksjon.METRIKKER_FIL if sti is None else Path(sti)
    ki_sti = Path(sti).with_name(KI_FILNAVN) if ki_sti is None else Path(ki_sti)
    etter_test = prediksjon.testkjoringer(sti) >= 1
    panel = {
        "mangler": True,
        "etter_test": etter_test,
        "periode": PERIODE_TEST if etter_test else PERIODE_VALIDERING,
        "antall_anlop": None,
        "horisonter": [],
    }
    try:
        data = json.loads(Path(sti).read_text(encoding="utf-8"))
        blokk = data["test" if etter_test else "validering"]
        panel["antall_anlop"] = _heltall(blokk["antall_anlop"])
        ki = les_ki(ki_sti) if etter_test else None
        panel["horisonter"] = [_horisont(etikett, blokk["horisonter"][h], etter_test, ki, h)
                               for h, etikett in HORISONTER]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        panel["antall_anlop"], panel["horisonter"] = None, []
        return panel
    panel["mangler"] = False
    return panel
