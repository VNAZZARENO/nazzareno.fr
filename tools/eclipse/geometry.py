"""Geometrie de deux disques apparents. Pur: pas d'ephemeride, pas d'E/S.

Toutes les grandeurs angulaires sont en degres.
"""

import math

__all__ = [
    "angular_separation", "disc_overlap_area", "eclipse_magnitude", "obscuration",
]


def angular_separation(az1, alt1, az2, alt2):
    """Separation angulaire entre deux directions du ciel, en degres.

    Formule de Vincenty: contrairement a acos(produit scalaire), elle reste
    precise aux tres petits angles, ce qui est exactement le regime d'une
    eclipse (quelques minutes d'arc autour du contact).
    """
    a1, d1, a2, d2 = map(math.radians, (az1, alt1, az2, alt2))
    da = a2 - a1
    num = math.hypot(
        math.cos(d2) * math.sin(da),
        math.cos(d1) * math.sin(d2) - math.sin(d1) * math.cos(d2) * math.cos(da),
    )
    den = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(da)
    return math.degrees(math.atan2(num, den))


def disc_overlap_area(d, r1, r2):
    """Aire d'intersection de deux disques de rayons r1 et r2 distants de d.

    Somme de deux segments circulaires. L'ecriture r^2*(a - sin(2a)/2) est
    preferee a la formule a racine carree: elle evite une annulation
    catastrophique quand les disques sont presque tangents.
    """
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = math.acos(max(-1.0, min(1.0, (d * d + r1 * r1 - r2 * r2) / (2.0 * d * r1))))
    a2 = math.acos(max(-1.0, min(1.0, (d * d + r2 * r2 - r1 * r1) / (2.0 * d * r2))))
    return r1 * r1 * (a1 - math.sin(2 * a1) / 2.0) + r2 * r2 * (a2 - math.sin(2 * a2) / 2.0)


def eclipse_magnitude(d, r_sun, r_moon):
    """Fraction du DIAMETRE solaire couverte. Convention usuelle:
    0 hors eclipse, 1 au contact interne quand les disques sont egaux,
    < 1 au maximum d'une annulaire, > 1 pour une totale.
    """
    if d >= r_sun + r_moon:
        return 0.0
    return (r_sun + r_moon - d) / (2.0 * r_sun)


def obscuration(d, r_sun, r_moon):
    """Fraction de l'AIRE du disque solaire couverte, entre 0 et 1.

    A ne pas confondre avec la fraction de flux (voir limb.py): l'aire ignore
    l'assombrissement centre-bord.
    """
    return disc_overlap_area(d, r_sun, r_moon) / (math.pi * r_sun * r_sun)
