"""Planetes et etoiles brillantes visibles au maximum de l'eclipse.

Le catalogue Hipparcos est telecharge par skyfield. S'il est indisponible, on
se rabat sur les seules planetes et on le signale: mieux vaut une page qui
annonce ce qui manque qu'une page qui invente.

Refraction: chaque astre recoit ici la sienne, calculee pour sa propre hauteur.
C'est volontairement different de `ephemeris.py`, qui souleve le Soleil et la
Lune d'un angle commun. Les deux regles repondent a deux questions distinctes.
Le Soleil et la Lune sont separes d'un demi-degre et c'est leur position
RELATIVE qui fait l'eclipse: les soulever separement deformerait ce qui est
justement calcule au millieme de degre pres. Les planetes et les etoiles, elles,
sont eparpillees sur toute la voute et ne sont couplees a rien; leur hauteur
apparente est tout ce qu'on leur demande, et rien ne justifierait de leur
appliquer le relevement du Soleil. Les conditions atmospheriques sont importees
d'`ephemeris.py` pour qu'elles n'aient qu'un seul endroit ou vivre.
"""

from skyfield.api import Star, load
from skyfield.data import hipparcos

from tools.eclipse.ephemeris import PRESSURE_MBAR, TEMPERATURE_C

REFRACTION = {"temperature_C": TEMPERATURE_C, "pressure_mbar": PRESSURE_MBAR}

PLANETES = {
    "Mercure": "mercury", "Venus": "venus", "Mars": "mars barycenter",
    "Jupiter": "jupiter barycenter", "Saturne": "saturn barycenter",
}

MAGNITUDE_LIMITE = 3.0


def planetes_visibles(eph, obs, t):
    sortie = []
    for nom, cle in PLANETES.items():
        app = obs.at(t).observe(eph[cle]).apparent()
        alt, az, _ = app.altaz(**REFRACTION)
        if alt.degrees > 0.0:
            sortie.append({"name": nom, "az": float(round(az.degrees, 3)),
                           "alt": float(round(alt.degrees, 3))})
    return sortie


def etoiles_visibles(obs, t):
    """Etoiles plus brillantes que MAGNITUDE_LIMITE et au-dessus de l'horizon.

    Rend (liste, catalogue_disponible).
    """
    try:
        with load.open(hipparcos.URL) as f:
            df = hipparcos.load_dataframe(f)
    except Exception:
        return [], False

    df = df[df["magnitude"] <= MAGNITUDE_LIMITE]
    df = df[df["ra_degrees"].notna()]

    sortie = []
    for hip, ligne in df.iterrows():
        app = obs.at(t).observe(Star.from_dataframe(ligne)).apparent()
        alt, az, _ = app.altaz(**REFRACTION)
        if alt.degrees > 0.0:
            sortie.append({"hip": int(hip), "mag": float(round(float(ligne["magnitude"]), 2)),
                           "az": float(round(az.degrees, 3)), "alt": float(round(alt.degrees, 3))})
    sortie.sort(key=lambda e: e["mag"])
    return sortie, True
