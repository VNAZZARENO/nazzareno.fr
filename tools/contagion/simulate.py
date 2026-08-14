"""Le monde temoin: un couple gaussien i.i.d. a correlation constante.

C'est la piece centrale de l'argument. Si la procedure des deciles fait monter
la correlation ICI, ou rien ne bouge par construction, alors la courbe montante
ne prouve rien en soi. La graine est fixee: la figure 2 est un calcul,
pas un alea.
"""
import numpy as np


def tirages(rho, n, graine):
    rng = np.random.default_rng(graine)
    x = rng.standard_normal(n)
    y = rho * x + np.sqrt(1.0 - rho * rho) * rng.standard_normal(n)
    return x, y


def correlation(x, y):
    """Pearson, diviseur n. Meme convention que l'explorateur JS: la parite en depend.

    Entree constante -> nan: aucun sous-echantillon degenere ne doit arriver ici."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    cx, cy = x - x.mean(), y - y.mean()
    return float((cx * cy).mean() / np.sqrt(cx.var() * cy.var()))
