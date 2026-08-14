"""Correlation glissante brute et corrigee, pour la figure des deux crises.

Ici le conditionnement n'est plus |x| du jour mais la fenetre qui glisse: le
delta est l'exces de variance de la fenetre sur la variance pleine periode.
C'est la version la plus proche des usages de place, et celle ou le biais
opere par la persistance de la volatilite.
"""
import numpy as np

from tools.contagion.bias import correction, delta_relatif
from tools.contagion.simulate import correlation


def glissantes(x, y, fenetre=60):
    """Correlation par fenetre, brute et corrigee. x est le marche SOURCE.

    Le delta vient de la variance de x seul: glissantes(x, y) et
    glissantes(y, x) ne disent pas la meme chose. La reference est la
    variance pleine periode, crises comprises: la correction SOUS-corrige
    donc, et c'est assume. Dans les fenetres calmes delta < 0 et la
    corrigee passe AU-DESSUS de la brute: l'inversion est symetrique,
    une variance sous la moyenne attenue la correlation d'echantillon.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    assert len(x) == len(y), "series de longueurs differentes"
    assert len(x) >= fenetre, "serie plus courte que la fenetre"
    var_pleine = x.var()
    n = len(x) - fenetre + 1
    brute = np.empty(n)
    corrigee = np.empty(n)
    delta = np.empty(n)
    for i in range(n):
        xf, yf = x[i:i + fenetre], y[i:i + fenetre]
        brute[i] = correlation(xf, yf)
        delta[i] = delta_relatif(xf.var(), var_pleine)
        corrigee[i] = correction(brute[i], delta[i])
    return brute, corrigee, delta
