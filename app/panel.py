"""Panelet «modell mot baseline» på hovedskjermen (E2-S09, PRD FR10, UX §2).

Modulen leser bare ``data/modell/metrikker.json`` (stien er ``app.prediksjon.METRIKKER_FIL``) og former tallene
for malen. Den regner ingenting fra utdrag eller prediksjoner. Hvert tall på skjermen er en verdi fra fila, bare
avrundet for visning. Unntakene er differansen modell − baseline i prosentpoeng og bestått/ikke bestått, som
sammenligner to verdier fra fila.

- Før testkjøringen (``testkjoringer() < 1``, samme funksjon som låsen) vises ``validering``-blokken, uten dom.
- Etter testkjøringen vises ``test``-blokken, med bestått/ikke bestått per horisont på modellutvalget.
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


def _dom(modell: dict, baseline: dict, varsle_alle: dict) -> list:
    """Bestått/ikke bestått på modellutvalget (FR10, beslutning 1): ±30 min over baseline og varsel-F1 over
    «varsle alle». Begge sammenligner verdier fra fila uavrundet. F1 vises med tre desimaler i dommen.
    Er F1 for «varsle alle» ``null``, kan F1-dommen ikke avgjøres."""
    treff_ok = modell["andel_30"] > baseline["andel_30"]
    f1_modell, f1_alle = modell["varsel"]["f1"], varsle_alle["f1"]
    if f1_alle is None:
        f1_dom = "kan ikke avgjøres"
    else:
        f1_dom = "bestått" if f1_modell is not None and f1_modell > f1_alle else "ikke bestått"
    return [
        f"Innenfor ±30 min: {'bestått' if treff_ok else 'ikke bestått'} "
        f"(modell {_pst(modell['andel_30'])}, baseline {_pst(baseline['andel_30'])})",
        f"Varsel-F1: {f1_dom} (modell {_f1(f1_modell, 3)}, «varsle alle» {_f1(f1_alle, 3)})",
    ]


# All Øvrige-trafikk: modellarmen er modellen pluss baselinen for anløpene modellen ikke brukes på, så raden
# viser «systemet», ikke «modellen» (Felipe, 11.11.2026).
SYSTEM = "Systemet"
FORKLARING_ALLE = ("De fleste forsinkelsene i all trafikk er turer inne i havneområdet, der modellen ikke brukes og "
                   "baselinen ikke kan varsle. Modellutvalget er raden som viser modellen.")


def _ovrige_gruppe(navn: str, blokk: dict, med_dom: bool, system: bool = False) -> dict:
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
        "dom": _dom(modell, baseline, alle) if med_dom else None,
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


def _horisont(etikett: str, h: dict, med_dom: bool) -> dict:
    ovrige, passasjer = h["antall"]["ovrige"], h["antall"]["passasjer"]
    return {
        "etikett": etikett,
        "fasit_ovrige": f"{_heltall(ovrige['med_fasit'])} av {_heltall(ovrige['rader'])}",
        "fasit_passasjer": f"{_heltall(passasjer['med_fasit'])} av {_heltall(passasjer['rader'])}",
        "modellandel": _andel_med_antall(h["andel_modellutvalg"]["med_fasit"],
                                         ovrige["modellutvalg_med_fasit"], ovrige["med_fasit"]),
        "grupper": [
            _ovrige_gruppe("Øvrige, modellutvalget", h["ovrige_modellutvalg"], med_dom),
            _ovrige_gruppe("Øvrige, alle (resten får baseline)", h["ovrige_alle"], False, system=True),
            _passasjer_gruppe(h["passasjer"]),
        ],
    }


def lag_panel(sti: Optional[Path] = None) -> dict:
    """Panelets innhold fra ``metrikker.json``. Kaster aldri: feil fil eller form gir ``mangler = True``."""
    sti = prediksjon.METRIKKER_FIL if sti is None else Path(sti)
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
        panel["horisonter"] = [_horisont(etikett, blokk["horisonter"][h], etter_test) for h, etikett in HORISONTER]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        panel["antall_anlop"], panel["horisonter"] = None, []
        return panel
    panel["mangler"] = False
    return panel
