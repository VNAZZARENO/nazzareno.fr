"""Telecharge les clotures Yahoo Finance une fois et les gele dans le depot.

Usage: source .venv/bin/activate && python3 -m tools.contagion.data

A ne relancer que pour geler un nouveau jeu: la page est datee, pas vivante.
Le manifeste enregistre symbole, source, horodatage et sommes SHA-256, pour
que le calcul soit rejouable sur exactement les memes octets. Le CSV est
reecrit par nos soins (Date,Open,High,Low,Close,Volume): le gel porte sur des
octets que NOUS avons produits, pas sur un format tiers susceptible de bouger.
"""
import datetime
import hashlib
import json
import math
import pathlib

import yfinance

RACINE = pathlib.Path(__file__).resolve().parents[2]
DOSSIER = RACINE / "tools" / "contagion" / "data"

SYMBOLES = {"spx.csv": "^GSPC", "cac.csv": "^FCHI"}


def _case(valeur):
    return "" if valeur is None or (isinstance(valeur, float) and math.isnan(valeur)) \
        else f"{valeur:.6f}"


def _volume(valeur):
    if valeur is None or (isinstance(valeur, float) and math.isnan(valeur)):
        return "0"
    return str(int(valeur))


def main():
    DOSSIER.mkdir(exist_ok=True)
    manifeste = {"telecharge_utc":
                 datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                 "fichiers": {}}
    for nom, symbole in SYMBOLES.items():
        histo = yfinance.Ticker(symbole).history(period="max", auto_adjust=False)
        histo = histo.dropna(subset=["Close"])
        if len(histo) < 5000:
            raise SystemExit(f"{symbole}: {len(histo)} lignes seulement")
        lignes = ["Date,Open,High,Low,Close,Volume"]
        for ts, l in histo.iterrows():
            lignes.append(",".join([ts.date().isoformat(), _case(l["Open"]),
                                    _case(l["High"]), _case(l["Low"]),
                                    _case(l["Close"]), _volume(l["Volume"])]))
        octets = ("\n".join(lignes) + "\n").encode("utf-8")
        (DOSSIER / nom).write_bytes(octets)
        manifeste["fichiers"][nom] = {
            "symbole": symbole,
            "source": f"Yahoo Finance via yfinance {yfinance.__version__}",
            "sha256": hashlib.sha256(octets).hexdigest(), "octets": len(octets)}
        print(nom, len(octets), "octets")
    (DOSSIER / "manifeste.json").write_text(
        json.dumps(manifeste, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
