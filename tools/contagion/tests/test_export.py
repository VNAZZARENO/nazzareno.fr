"""Le contrat entre Python et la page: contenu, budget, fixtures."""
import json
import pathlib

import pytest

from tools.contagion.bias import correction, delta_relatif
from tools.contagion.export import (
    QUANTILES_FIXTURE, _variance, construire, ecrire, sous_echantillon)
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation

RACINE = pathlib.Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def artefacts():
    chemin_json = RACINE / "assets" / "data" / "contagion.json"
    chemin_fix = RACINE / "tools" / "js-tests" / "fixture-contagion.json"
    avant = (chemin_json.read_bytes(), chemin_fix.read_bytes())
    ecrire()
    apres = (chemin_json.read_bytes(), chemin_fix.read_bytes())
    assert avant == apres, \
        "artefacts commites perimes: relancer python3 -m tools.contagion.export et commiter"
    return json.loads(apres[0]), json.loads(apres[1])


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
    assert octets < 200_000, f"{octets} octets: budget 200 Ko depasse, spec section 12"


def test_fixtures_de_parite(artefacts):
    donnees, fixture = artefacts
    assert [c["q"] for c in fixture["cas"]] == [0.0, 0.5, 0.9, 0.95]
    for cas in fixture["cas"]:
        for cle in ("n", "delta", "rho", "rho_corrigee"):
            assert cle in cas
    # les fixtures sont calculees sur les MEMES tableaux arrondis que le JSON servi
    assert fixture["rho_pleine"] == pytest.approx(
        correlation(donnees["rx"], donnees["ry"]), abs=1e-12)
    # epingler les cas individuels contre les valeurs calculees de la page
    var_pleine = _variance(donnees["rx"])
    for cas in fixture["cas"]:
        sx, sy = sous_echantillon(donnees["rx"], donnees["ry"], cas["q"])
        delta = delta_relatif(_variance(sx), var_pleine)
        rho = correlation(sx, sy)
        assert cas["n"] == len(sx)
        assert cas["delta"] == pytest.approx(delta, abs=1e-12)
        assert cas["rho"] == pytest.approx(rho, abs=1e-12)
        assert cas["rho_corrigee"] == pytest.approx(correction(rho, delta), abs=1e-12)
