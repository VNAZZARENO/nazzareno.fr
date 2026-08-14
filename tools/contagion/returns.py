"""Des CSV geles aux paires de rendements comparables.

Paris ferme a 17 h 30, New York a 22 h: les rendements du meme jour calendaire
ne se recouvrent que partiellement. On suit Forbes et Rigobon eux-memes:
rendements logarithmiques en moyenne mobile 2 jours, calcules sur le calendrier
propre de chaque marche, puis apparies sur l'intersection des dates. Le prix de
ce choix, une autocorrelation MA(1), est declare dans la page et verifie par
test plutot que passe sous silence.
"""
import csv
import pathlib

import numpy as np

DOSSIER = pathlib.Path(__file__).resolve().parent / "data"


def _lire_csv(nom):
    with open(DOSSIER / nom, newline="", encoding="utf-8") as f:
        lignes = [l for l in csv.DictReader(f) if l.get("Close")]
    return [l["Date"] for l in lignes], np.array([float(l["Close"]) for l in lignes])


def rendements_log(dates, clotures):
    r = np.diff(np.log(np.asarray(clotures)))
    return list(dates[1:]), r


def paires(dates, rendements):
    """Moyenne mobile 2 jours sur le calendrier propre: (r_t + r_{t-1}) / 2."""
    r2 = (rendements[1:] + rendements[:-1]) / 2.0
    return list(dates[1:]), r2


def serie_appariee(dates_a, r_a, dates_b, r_b):
    communes = sorted(set(dates_a) & set(dates_b))
    ia = {d: i for i, d in enumerate(dates_a)}
    ib = {d: i for i, d in enumerate(dates_b)}
    xa = np.array([r_a[ia[d]] for d in communes])
    xb = np.array([r_b[ib[d]] for d in communes])
    return communes, xa, xb


def charger_cloture(ma2=True):
    """La chaine complete: CSV geles -> dates communes, rx (S&P), ry (CAC)."""
    series = {}
    for cle, nom in (("x", "spx.csv"), ("y", "cac.csv")):
        d, c = _lire_csv(nom)
        d, r = rendements_log(d, c)
        if ma2:
            d, r = paires(d, r)
        series[cle] = (d, r)
    return serie_appariee(*series["x"], *series["y"])
