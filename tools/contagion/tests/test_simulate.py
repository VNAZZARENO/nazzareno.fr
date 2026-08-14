"""Le Monte-Carlo doit retomber sur la formule: c'est la validation du projet."""
import numpy as np
import pytest

from tools.contagion.bias import correction, delta_relatif, rho_conditionnelle
from tools.contagion.simulate import correlation, tirages

RHO, N, GRAINE = 0.58, 500_000, 20260814


def test_tirages_reproductibles_et_calibres():
    x1, y1 = tirages(RHO, N, GRAINE)
    x2, y2 = tirages(RHO, N, GRAINE)
    assert np.array_equal(x1, x2) and np.array_equal(y1, y2)
    assert correlation(x1, y1) == pytest.approx(RHO, abs=3 * (1 - RHO**2) / np.sqrt(N))


def test_conditionnement_suit_la_formule():
    """Correlation des sous-echantillons |x| >= quantile: la formule, pas plus."""
    x, y = tirages(RHO, N, GRAINE)
    var_pleine = x.var()
    for q in (0.5, 0.8, 0.95):
        seuil = np.sort(np.abs(x))[int(q * len(x))]
        garde = np.abs(x) >= seuil
        rho_obs = correlation(x[garde], y[garde])
        delta = delta_relatif(x[garde].var(), var_pleine)
        attendu = rho_conditionnelle(RHO, delta)
        tolerance = 3 * (1 - attendu**2) / np.sqrt(garde.sum())
        assert rho_obs == pytest.approx(attendu, abs=tolerance), q
        # et la correction retrouve la valeur vraie dans le meme intervalle
        assert correction(rho_obs, delta) == pytest.approx(RHO, abs=tolerance)
