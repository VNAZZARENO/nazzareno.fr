"""Enveloppe skyfield: un lieu et une grille de temps donnent une serie d'etats.

Seul module a dependre de DE440s. Tout le reste du calcul est pur.
"""

import math
from dataclasses import dataclass

from skyfield.api import load, wgs84

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
    """Etat topocentrique apparent, refraction comprise."""
    sun = obs.at(t).observe(eph["sun"]).apparent()
    moon = obs.at(t).observe(eph["moon"]).apparent()

    sun_alt, sun_az, sun_dist = sun.altaz(
        temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)
    moon_alt, moon_az, moon_dist = moon.altaz(
        temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)

    return State(
        sun_az=float(sun_az.degrees),
        sun_alt=float(sun_alt.degrees),
        moon_az=float(moon_az.degrees),
        moon_alt=float(moon_alt.degrees),
        r_sun=float(math.degrees(math.asin(R_SUN_KM / sun_dist.km))),
        r_moon=float(math.degrees(math.asin(R_MOON_KM / moon_dist.km))),
        d_sun_km=float(sun_dist.km),
        d_moon_km=float(moon_dist.km),
    )
