"""Ecrit assets/data/contagion.json et les fixtures de parite JS.

Usage: source .venv/bin/activate && python3 -m tools.contagion.export

Le JSON ne porte pas les dates: l'explorateur n'en a pas besoin, seules les
bornes vont dans meta (ecart assume a la spec, note dans le plan). Point
crucial de la parite: les fixtures sont calculees sur les tableaux ARRONDIS,
exactement ceux que le navigateur recevra, pas sur les flottants d'origine.
"""
import json
import pathlib

from tools.contagion.bias import correction, delta_relatif
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE_JSON = RACINE / "assets" / "data" / "contagion.json"
SORTIE_FIXTURE = RACINE / "tools" / "js-tests" / "fixture-contagion.json"
QUANTILES_FIXTURE = [0.0, 0.5, 0.9, 0.95]


def sous_echantillon(rx, ry, q):
    """Convention unique du seuil, dupliquee a l'identique dans explorer.js.

    Domaine: 0 <= q < 1. La valeur q=1 leverait IndexError; le curseur de
    la page est borne en dessous.
    """
    ampl = sorted(abs(v) for v in rx)
    seuil = ampl[int(q * len(ampl))] if q > 0.0 else 0.0
    couples = [(a, b) for a, b in zip(rx, ry) if abs(a) >= seuil]
    return [a for a, _ in couples], [b for _, b in couples]


def construire():
    dates, rx, ry = charger_cloture()
    rx6 = [round(float(v), 6) for v in rx]
    ry6 = [round(float(v), 6) for v in ry]
    donnees = {
        "meta": {"source": "Yahoo Finance via yfinance, clotures quotidiennes, voir tools/contagion/data",
                 "series": "S&P 500 (x), CAC 40 (y), rendements log en moyenne mobile 2 j",
                 "debut": dates[0], "fin": dates[-1], "n": len(rx6)},
        "rx": rx6, "ry": ry6,
    }
    var_pleine = _variance(rx6)
    cas = []
    for q in QUANTILES_FIXTURE:
        sx, sy = sous_echantillon(rx6, ry6, q)
        delta = delta_relatif(_variance(sx), var_pleine)
        rho = correlation(sx, sy)
        cas.append({"q": q, "n": len(sx), "delta": delta, "rho": rho,
                    "rho_corrigee": correction(rho, delta)})
    fixture = {"rho_pleine": correlation(rx6, ry6), "cas": cas}
    return donnees, fixture


def _variance(valeurs):
    m = sum(valeurs) / len(valeurs)
    return sum((v - m) ** 2 for v in valeurs) / len(valeurs)


def ecrire():
    donnees, fixture = construire()
    SORTIE_JSON.write_text(json.dumps(donnees, separators=(",", ":"), allow_nan=False) + "\n")
    SORTIE_FIXTURE.write_text(json.dumps(fixture, indent=1, allow_nan=False) + "\n")
    print(SORTIE_JSON, SORTIE_JSON.stat().st_size, "octets")


if __name__ == "__main__":
    ecrire()
