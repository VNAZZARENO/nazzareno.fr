"""Planetes et etoiles brillantes visibles au maximum de l'eclipse.

Le catalogue Hipparcos est telecharge par skyfield. S'il est indisponible, on
se rabat sur les seules planetes et on le signale: mieux vaut une page qui
annonce ce qui manque qu'une page qui invente.
"""

from skyfield.api import Star, load
from skyfield.data import hipparcos

PLANETES = {
    "Mercure": "mercury", "Venus": "venus", "Mars": "mars barycenter",
    "Jupiter": "jupiter barycenter", "Saturne": "saturn barycenter",
}

MAGNITUDE_LIMITE = 3.0


def planetes_visibles(eph, obs, t):
    sortie = []
    for nom, cle in PLANETES.items():
        app = obs.at(t).observe(eph[cle]).apparent()
        alt, az, _ = app.altaz()
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
        alt, az, _ = app.altaz()
        if alt.degrees > 0.0:
            sortie.append({"hip": int(hip), "mag": float(round(float(ligne["magnitude"]), 2)),
                           "az": float(round(az.degrees, 3)), "alt": float(round(alt.degrees, 3))})
    sortie.sort(key=lambda e: e["mag"])
    return sortie, True
