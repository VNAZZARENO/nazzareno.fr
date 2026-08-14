import numpy as np
import pytest

from tools.contagion.bias import correction
from tools.contagion.simulate import correlation, tirages
from tools.contagion.rolling import glissantes

FENETRE = 60


def test_dimensions_et_premier_point():
    x, y = tirages(0.5, 300, 7)
    brute, corrigee, delta = glissantes(x, y, fenetre=FENETRE)
    assert len(brute) == len(corrigee) == len(delta) == 300 - FENETRE + 1
    assert brute[0] == pytest.approx(correlation(x[:FENETRE], y[:FENETRE]))


def test_sur_monde_constant_la_corrigee_reste_au_niveau():
    rho = 0.5
    x, y = tirages(rho, 20_000, 11)
    # on recupere le bruit propre implicite de y, puis on gonfle le seul choc
    # commun x sur un segment: c'est le monde de Forbes-Rigobon, ou la crise
    # grossit x sans toucher au bruit. La brute doit monter (rapport signal
    # sur bruit), la corrigee doit rester au niveau vrai en moyenne.
    z = (y - rho * x) / np.sqrt(1.0 - rho * rho)
    x2 = x.copy()
    x2[8000:9000] *= 3.0
    y2 = rho * x2 + np.sqrt(1.0 - rho * rho) * z
    brute, corrigee, _ = glissantes(x2, y2, fenetre=FENETRE)
    segment = slice(8000 + FENETRE, 9000 - FENETRE)
    assert np.mean(brute[segment]) > 0.75
    # la reference de variance est la PLEINE periode, crise comprise: c'est le
    # choix assume du module (il sous-corrige, donc il joue contre la these de
    # la page). La valeur attendue s'en deduit, on ne compare pas a rho nu.
    rho_seg = 3 * rho / np.sqrt(9 * rho**2 + 1 - rho**2)
    var_pleine_pop = (19_000 * 1.0 + 1_000 * 9.0) / 20_000
    attendu = correction(rho_seg, 9.0 / var_pleine_pop - 1.0)
    assert abs(np.mean(corrigee[segment]) - attendu) < 0.05
