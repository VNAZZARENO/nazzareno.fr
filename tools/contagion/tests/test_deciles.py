"""Les deciles portent les figures 1 a 3: leurs proprietes affichees sont testees ici."""
import numpy as np
import pytest

from tools.contagion.simulate import tirages
from tools.contagion.deciles import par_deciles

RHO, N, GRAINE = 0.58, 9000, 20260814


@pytest.fixture(scope="module")
def tranches():
    x, y = tirages(RHO, N, GRAINE)
    return par_deciles(x, y, graine_bootstrap=GRAINE)


def test_structure(tranches):
    assert len(tranches) == 10
    for t in tranches:
        for cle in ("rho", "rho_corrigee", "delta", "n", "amplitude_mediane",
                    "ic_bas", "ic_haut", "ic_corr_bas", "ic_corr_haut"):
            assert cle in t
    assert sum(t["n"] for t in tranches) == N


def test_courbe_brute_monte_courbe_corrigee_plate(tranches):
    bruts = [t["rho"] for t in tranches]
    assert bruts[-1] - bruts[0] > 0.3, "le biais doit se voir sur un monde a rho constant"
    # la correction n'est affirmable que la ou l'estimateur est serre: l'inversion
    # F-R amplifie le bruit ~1/sqrt(1+delta) dans les deciles bas. Deux proprietes:
    # (1) l'IC corrige encadre la vraie valeur partout,
    # (2) la platitude se lit sur les deciles 3 a 10, ou l'ecart-type est petit.
    for t in tranches:
        assert t["ic_corr_bas"] < RHO < t["ic_corr_haut"]
    corriges_serres = [t["rho_corrigee"] for t in tranches[2:]]
    assert max(abs(c - RHO) for c in corriges_serres) < 0.12


def test_bootstrap_reproductible_et_ordonne(tranches):
    x, y = tirages(RHO, N, GRAINE)
    bis = par_deciles(x, y, graine_bootstrap=GRAINE)
    assert [t["ic_bas"] for t in bis] == [t["ic_bas"] for t in tranches]
    for t in tranches:
        assert t["ic_bas"] < t["rho"] < t["ic_haut"]
        assert t["ic_corr_bas"] < t["rho_corrigee"] < t["ic_corr_haut"]
