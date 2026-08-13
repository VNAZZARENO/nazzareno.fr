"""Assombrissement centre-bord du Soleil et fraction de flux non occultee.

Module pur. Voir NASA-REFERENCE.md pour la source des coefficients.

Le point physique, souvent mal enonce: pendant une partielle profonde la Lune
couvre le CENTRE du disque et ne laisse qu'un croissant au LIMBE, qui est la
partie la plus sombre. Le flux residuel passe donc SOUS la valeur naive
1 - obscuration. Ce qui fait qu'une partielle a 90 % se vit comme du plein
jour n'est pas la, mais dans la reponse logarithmique de l'oeil.
"""

import math

__all__ = ["intensity", "visible_flux_fraction", "rgb_flux_fraction", "SRGB_LIMB_COEFFS"]

# Loi quadratique I(mu)/I(1) = 1 - u1 (1-mu) - u2 (1-mu)^2,
# aux longueurs d'onde des primaires sRGB, dans l'ordre (rouge, vert, bleu).
# Source: Pierce & Slaughter (1977), Table III. Voir NASA-REFERENCE.md.
SRGB_LIMB_COEFFS = (
    (0.37712, 0.27635),  # rouge  610.975 nm
    (0.43044, 0.27494),  # vert   552.200 nm
    (0.57264, 0.21241),  # bleu   468.306 nm
)


def intensity(mu, u1, u2):
    """Intensite specifique normalisee, mu = cos(angle depuis le centre du disque).

    mu = 1 au centre du disque, mu = 0 au limbe.
    """
    v = 1.0 - mu
    return 1.0 - u1 * v - u2 * v * v


def visible_flux_fraction(d, r_sun, r_moon, u1, u2, n=2048):
    """Fraction du flux solaire non occultee, ponderee par l'assombrissement.

    L'integrale sur le disque est reduite a une dimension: pour un anneau de
    rayon rho, la Lune en masque un arc dont le demi-angle vaut
    acos((rho^2 + d^2 - r_moon^2) / (2 rho d)). La fraction visible de
    l'anneau est donc 1 - arc/pi, sans aucune integration angulaire.
    """
    if d >= r_sun + r_moon:
        return 1.0

    total = 0.0
    visible = 0.0
    for i in range(n):
        rho = (i + 0.5) / n * r_sun
        mu = math.sqrt(max(0.0, 1.0 - (rho / r_sun) ** 2))
        poids = intensity(mu, u1, u2) * rho
        total += poids

        if d <= 0.0:
            fraction = 0.0 if rho < r_moon else 1.0
        else:
            c = (rho * rho + d * d - r_moon * r_moon) / (2.0 * rho * d)
            if c >= 1.0:
                fraction = 1.0      # l'anneau est entierement hors de la Lune
            elif c <= -1.0:
                fraction = 0.0      # l'anneau est entierement dans la Lune
            else:
                fraction = 1.0 - math.acos(c) / math.pi
        visible += poids * fraction

    return visible / total


def rgb_flux_fraction(d, r_sun, r_moon, n=2048):
    """Fraction de flux visible sur les trois canaux, dans l'ordre (r, v, b)."""
    return tuple(
        visible_flux_fraction(d, r_sun, r_moon, u1, u2, n=n)
        for u1, u2 in SRGB_LIMB_COEFFS
    )
