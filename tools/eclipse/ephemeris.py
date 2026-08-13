"""Enveloppe skyfield: un lieu et une grille de temps donnent une serie d'etats.

Seul module a dependre de DE440s. Tout le reste du calcul est pur.
"""

import math
from dataclasses import dataclass

from skyfield.api import load, wgs84
from skyfield.earthlib import refract

R_SUN_KM = 695_700.0
R_MOON_KM = 1_737.4

# Conditions standard pour la refraction. Elles ne changent pas la geometrie,
# seulement l'altitude apparente -- ce qui compte en Espagne ou le Soleil frise
# l'horizon.
TEMPERATURE_C = 15.0
PRESSURE_MBAR = 1013.25


@dataclass(frozen=True)
class Site:
    id: str
    name_fr: str
    name_en: str
    lat: float
    lon: float
    elevation_m: float
    tz: str


@dataclass(frozen=True)
class State:
    """Etat instantane vu depuis un lieu. Angles en degres, distances en km."""
    sun_az: float
    sun_alt: float
    moon_az: float
    moon_alt: float
    r_sun: float      # rayon angulaire apparent du Soleil
    r_moon: float     # rayon angulaire apparent de la Lune
    d_sun_km: float
    d_moon_km: float


def open_ephemeris(name="de440s.bsp"):
    """Charge l'ephemeride JPL et l'echelle de temps. Telecharge au besoin."""
    eph = load(name)
    return eph, load.timescale()


def observer(eph, site):
    return eph["earth"] + wgs84.latlon(site.lat, site.lon, elevation_m=site.elevation_m)


def state_at(eph, obs, t):
    """Etat topocentrique apparent, refraction comprise.

    La refraction souleve les deux astres du MEME angle, celui calcule pour le
    Soleil. C'est exactement ce qu'annonce l'en-tete du module: elle ne change
    pas la geometrie, seulement l'altitude apparente.

    Laisser skyfield refracter chaque astre separement ferait le contraire. Son
    modele coupe net la refraction sous -1 deg de hauteur vraie (voir
    `skyfield.earthlib.refraction`), et le Soleil franchit ce seuil une
    vingtaine de secondes avant la Lune, qui le suit d'un demi-degre. Pendant
    ces vingt secondes l'un est refracte et l'autre non: la separation des deux
    disques bondit de 0.55 deg, soit plus que la somme de leurs rayons. A Palma,
    ou C4 tombe une demi-heure apres le coucher du Soleil, l'artefact tombe en
    pleine phase partielle et donnerait une image ou le Soleil parait libre de
    toute occultation. Un decalage commun ne peut pas produire cela.

    Il reste une marche, celle du modele lui-meme, quand le Soleil passe sous
    -1 deg: les deux hauteurs sautent alors ensemble de 0.44 deg. Elle est sans
    effet sur la geometrie, et se produit sous l'horizon, la ou plus rien n'est
    observable.
    """
    ici = obs.at(t)
    sun = ici.observe(eph["sun"]).apparent()
    moon = ici.observe(eph["moon"]).apparent()

    # Hauteurs vraies, sans refraction: c'est sur elles que porte la geometrie.
    sun_alt, sun_az, sun_dist = sun.altaz()
    moon_alt, moon_az, moon_dist = moon.altaz()

    releve = float(refract(sun_alt.degrees, TEMPERATURE_C, PRESSURE_MBAR)
                   - sun_alt.degrees)

    return State(
        sun_az=float(sun_az.degrees),
        sun_alt=float(sun_alt.degrees) + releve,
        moon_az=float(moon_az.degrees),
        moon_alt=float(moon_alt.degrees) + releve,
        r_sun=float(math.degrees(math.asin(R_SUN_KM / sun_dist.km))),
        r_moon=float(math.degrees(math.asin(R_MOON_KM / moon_dist.km))),
        d_sun_km=float(sun_dist.km),
        d_moon_km=float(moon_dist.km),
    )
