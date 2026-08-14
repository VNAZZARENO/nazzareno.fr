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
    x, y = np.asarray(x, float), np.asarray(y, float)
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
