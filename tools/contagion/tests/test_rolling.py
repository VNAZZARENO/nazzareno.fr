import numpy as np
import pytest

from tools.contagion.simulate import correlation, tirages
from tools.contagion.rolling import glissantes

FENETRE = 60


def test_dimensions_et_premier_point():
    x, y = tirages(0.5, 300, 7)
    brute, corrigee, delta = glissantes(x, y, fenetre=FENETRE)
    assert len(brute) == len(corrigee) == len(delta) == 300 - FENETRE + 1
    assert brute[0] == pytest.approx(correlation(x[:FENETRE], y[:FENETRE]))


def test_sur_monde_constant_la_corrigee_reste_au_niveau():
    x, y = tirages(0.5, 20_000, 11)
    # variance locale gonflee artificiellement sur un segment: le delta monte dans
    # la fenetre. Meme si la brute reste stable (correlation scale-invariante),
    # le delta mesure bien l'exces de variance de la fenetre sur la periode.
    x2, y2 = x.copy(), y.copy()
    x2[8000:9000] *= 3.0
    y2[8000:9000] *= 3.0
    brute, corrigee, delta = glissantes(x2, y2, fenetre=FENETRE)
    segment = slice(8000 + FENETRE, 9000 - FENETRE)
    assert np.mean(delta[segment]) > 3.0
    assert abs(np.mean(brute[segment]) - 0.5) < 0.15
