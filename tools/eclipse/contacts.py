"""Recherche des instants de contact C1 a C4 par recherche de racine.

`separation` est une fonction du temps (en secondes depuis une origine
arbitraire) qui rend la separation angulaire en degres. Le module ne sait rien
des ephemerides: c'est ce qui le rend testable avec des fonctions analytiques.
"""

from scipy.optimize import brentq

__all__ = ["find_contacts"]


def _minimum_grossier(separation, t0, t1, n=2000):
    pas = (t1 - t0) / n
    t_min, d_min = t0, separation(t0)
    for i in range(1, n + 1):
        t = t0 + i * pas
        d = separation(t)
        if d < d_min:
            t_min, d_min = t, d
    return t_min, d_min


def _racine(separation, cible, a, b):
    """Racine de separation(t) = cible sur [a, b], ou None si pas d'encadrement."""
    fa = separation(a) - cible
    fb = separation(b) - cible
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        return None
    return brentq(lambda t: separation(t) - cible, a, b, xtol=1e-6)


def find_contacts(separation, t0, t1, r_sun, r_moon):
    """Rend {'c1','c2','c3','c4'} en secondes, valeurs None si le contact
    n'a pas lieu.

    C1 et C4: d = r_sun + r_moon (contacts exterieurs).
    C2 et C3: d = |r_sun - r_moon| (contacts interieurs, totalite ou annulaire).
    """
    t_min, d_min = _minimum_grossier(separation, t0, t1)

    externe = r_sun + r_moon
    interne = abs(r_sun - r_moon)

    contacts = {"c1": None, "c2": None, "c3": None, "c4": None}
    if d_min >= externe:
        return contacts

    contacts["c1"] = _racine(separation, externe, t0, t_min)
    contacts["c4"] = _racine(separation, externe, t_min, t1)
    if d_min < interne:
        contacts["c2"] = _racine(separation, interne, t0, t_min)
        contacts["c3"] = _racine(separation, interne, t_min, t1)
    return contacts
