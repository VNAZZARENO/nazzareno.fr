"""Le jeu gele est present, integre, et assez profond pour la page."""
import csv
import datetime
import hashlib
import json
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[3]
DOSSIER = RACINE / "tools" / "contagion" / "data"


def lire(nom):
    with open(DOSSIER / nom, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_manifeste_et_sommes():
    manifeste = json.loads((DOSSIER / "manifeste.json").read_text())
    assert set(manifeste["fichiers"]) == {"spx.csv", "cac.csv"}
    for nom, attendu in manifeste["fichiers"].items():
        sha = hashlib.sha256((DOSSIER / nom).read_bytes()).hexdigest()
        assert sha == attendu["sha256"], nom
        assert attendu["symbole"] in ("^GSPC", "^FCHI")
        assert attendu["source"].startswith("Yahoo Finance via yfinance")
    assert "telecharge_utc" in manifeste


def test_pas_de_seance_en_cours():
    manifeste = json.loads((DOSSIER / "manifeste.json").read_text())
    jour_gel = datetime.datetime.fromisoformat(manifeste["telecharge_utc"]).date()
    for nom in ("spx.csv", "cac.csv"):
        derniere = datetime.date.fromisoformat(lire(nom)[-1]["Date"])
        assert derniere < jour_gel, f"{nom}: derniere ligne {derniere} pas reglee"


def test_profondeur_et_ordre():
    for nom in ("spx.csv", "cac.csv"):
        lignes = lire(nom)
        dates = [datetime.date.fromisoformat(l["Date"]) for l in lignes]
        assert dates == sorted(dates), f"{nom}: dates non croissantes"
        assert len(set(dates)) == len(dates), f"{nom}: doublons"
        assert (dates[-1] - dates[0]).days > 25 * 365, f"{nom}: historique court"
        for l in lignes:
            assert float(l["Close"]) > 0.0
