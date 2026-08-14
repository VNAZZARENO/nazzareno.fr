"""Le contrat entre Python et la page: contenu, budget, fixtures."""
import json
import pathlib

import pytest

from tools.contagion.export import construire, ecrire
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation

RACINE = pathlib.Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def artefacts():
    ecrire()
    donnees = json.loads((RACINE / "assets" / "data" / "contagion.json").read_text())
    fixture = json.loads((RACINE / "tools" / "js-tests" / "fixture-contagion.json").read_text())
    return donnees, fixture


def test_contenu_et_coherence(artefacts):
    donnees, _ = artefacts
    dates, rx, ry = charger_cloture()
    assert donnees["meta"]["n"] == len(rx) == len(donnees["rx"]) == len(donnees["ry"])
    assert donnees["meta"]["debut"] == dates[0] and donnees["meta"]["fin"] == dates[-1]
    # l'arrondi a 6 decimales ne doit pas deplacer la correlation avant la 5e
    rho_exact = correlation(rx, ry)
    rho_arrondi = correlation(donnees["rx"], donnees["ry"])
    assert abs(rho_exact - rho_arrondi) < 1e-5


def test_budget_de_taille(artefacts):
    octets = (RACINE / "assets" / "data" / "contagion.json").stat().st_size
    assert octets < 200_000, f"{octets} octets: budget ~150 Ko creve, spec section 12"


def test_fixtures_de_parite(artefacts):
    donnees, fixture = artefacts
    assert [c["q"] for c in fixture["cas"]] == [0.0, 0.5, 0.9]
    for cas in fixture["cas"]:
        for cle in ("n", "delta", "rho", "rho_corrigee"):
            assert cle in cas
    # les fixtures sont calculees sur les MEMES tableaux arrondis que le JSON servi
    assert fixture["rho_pleine"] == pytest.approx(
        correlation(donnees["rx"], donnees["ry"]), abs=1e-12)
