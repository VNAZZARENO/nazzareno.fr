"""Assemble le calcul complet et ecrit assets/data/eclipse-2026-08-12.json.

Usage: source .venv/bin/activate && python3 -m tools.eclipse.build

A lancer depuis la RACINE du depot. Le fichier produit, lui, est ecrit a la
bonne place quel que soit le repertoire courant, mais `open_ephemeris()` cherche
`de440s.bsp` a cote du repertoire courant: depuis ailleurs, skyfield ne le
trouverait pas et retelechargerait 32 Mo sans rien dire.

Convention du fichier produit, celle que reprendra `assets/js/eclipse/data.js`:
`t0_utc` est l'origine des temps, `step_s` le pas, `frames[i]` decrit l'instant
t = i * step_s, et les quatre contacts comme `t_max_s` sont donnes en SECONDES
depuis cette meme origine. Tout est donc sur un seul axe, indexable sans
conversion de date.
"""

import json
import math
import pathlib

import skyfield

from tools.eclipse import geometry, limb
from tools.eclipse.contacts import find_contacts
from tools.eclipse.ephemeris import Site, open_ephemeris, observer, state_at
from tools.eclipse.sky_objects import planetes_visibles, etoiles_visibles

# Ancre sur la racine du depot: le script doit pouvoir tourner depuis ailleurs
# que le repertoire courant sans ecrire le fichier au mauvais endroit.
RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "assets" / "data" / "eclipse-2026-08-12.json"

PAS_S = 20
MARGE_S = 300           # 5 min de part et d'autre de C1 et C4
FENETRE_UTC = (2026, 8, 12, 14, 0, 0)   # debut de la recherche grossiere
DUREE_RECHERCHE_S = 8 * 3600

ANNEAUX_FLUX = 512      # subdivisions radiales de l'integrale de flux

# Nombre d'etoiles conservees au maximum. Au-dela de la soixantaine la plus
# brillante, on paierait des octets pour des points que personne ne distingue.
ETOILES_MAX = 60

SITES = [
    Site("paris", "Paris", "Paris", 48.8566, 2.3522, 35.0, "Europe/Paris"),
    Site("espagne", "Palma de Majorque", "Palma de Mallorca",
         39.571147, 2.651817, 24.0, "Europe/Madrid"),
    Site("reykjavik", "Reykjavík", "Reykjavík", 64.1466, -21.9426, 30.0,
         "Atlantic/Reykjavik"),
]


def _instant(ts, t_origine, t_s):
    return ts.tt_jd(t_origine.tt + t_s / 86400.0)


def _separation_fn(eph, obs, ts, t_origine, somme_ref):
    """Rend separation(t en secondes depuis t_origine) -> degres, corrigee de
    la derive des rayons apparents.

    `find_contacts` compare la separation a des seuils CONSTANTS, alors que les
    rayons apparents, eux, varient sur les huit heures de la fenetre: la
    parallaxe lunaire suffit a faire bouger r_moon de quelques secondes d'arc
    entre le moment ou la Lune est haute et celui ou elle touche l'horizon. Pris
    au pied de la lettre, un seuil fige decale C4 de 7 s a Palma -- davantage
    que la tolerance de 5 s de l'etape de validation.

    On retranche donc a la separation la derive de la somme des rayons. C1 et C4
    tombent alors exactement sur d(t) = r_sun(t) + r_moon(t). Pour C2 et C3 le
    seuil vise devient |R_sun - R_moon| + 2 (r_sun(t) - R_sun), soit une erreur
    de deux fois la derive du seul rayon solaire: le Soleil ne bouge pas d'un
    centieme de seconde d'arc en huit heures, c'est negligeable.
    """
    def separation(t_s):
        st = state_at(eph, obs, _instant(ts, t_origine, t_s))
        d = geometry.angular_separation(
            st.sun_az, st.sun_alt, st.moon_az, st.moon_alt)
        return d - (st.r_sun + st.r_moon) + somme_ref
    return separation


def _image(st, d):
    """Les treize champs d'une image, et la magnitude non arrondie."""
    mag = max(0.0, geometry.eclipse_magnitude(d, st.r_sun, st.r_moon))
    obsc = geometry.obscuration(d, st.r_sun, st.r_moon)
    f_r, f_v, f_b = limb.rgb_flux_fraction(d, st.r_sun, st.r_moon, n=ANNEAUX_FLUX)

    mag_arr, obsc_arr = round(mag, 5), round(obsc, 5)
    # Magnitude et obscuration doivent s'annuler ensemble: c'est le meme fait
    # ("les disques ne se touchent pas") lu de deux facons. Elles ne tendent pas
    # vers zero a la meme vitesse -- l'obscuration part comme la puissance 3/2
    # de la magnitude -- si bien qu'a une seconde du contact l'arrondi peut
    # annuler l'une sans l'autre. On les annule alors toutes les deux: a cette
    # precision la difference entre les deux lectures n'a plus de sens.
    if mag_arr == 0.0 or obsc_arr == 0.0:
        mag_arr = obsc_arr = 0.0

    return [
        round(st.sun_az, 4), round(st.sun_alt, 4),
        round(st.moon_az, 4), round(st.moon_alt, 4),
        round(st.r_sun, 6), round(st.r_moon, 6),
        mag_arr, obsc_arr,
        round(f_r, 6), round(f_v, 6), round(f_b, 6),
        round(st.d_sun_km, 1), round(st.d_moon_km, 3),
    ], mag


def construire_site(eph, ts, site, journal):
    obs = observer(eph, site)
    t_origine = ts.utc(*FENETRE_UTC)

    st_ref = state_at(eph, obs, _instant(ts, t_origine, DUREE_RECHERCHE_S / 2))
    separation = _separation_fn(eph, obs, ts, t_origine, st_ref.r_sun + st_ref.r_moon)

    contacts = find_contacts(separation, 0.0, DUREE_RECHERCHE_S,
                             st_ref.r_sun, st_ref.r_moon)
    if contacts["c1"] is None or contacts["c4"] is None:
        raise SystemExit(f"aucune eclipse visible depuis {site.id}")

    # Origine calee sur une seconde entiere: `t0_utc` est alors exact a la
    # seconde et les images tombent sur des instants ronds.
    debut = float(math.floor(contacts["c1"] - MARGE_S))
    fin = contacts["c4"] + MARGE_S
    n = int((fin - debut) // PAS_S) + 1

    images = []
    i_max, mag_max = 0, -1.0
    for i in range(n):
        st = state_at(eph, obs, _instant(ts, t_origine, debut + i * PAS_S))
        d = geometry.angular_separation(st.sun_az, st.sun_alt, st.moon_az, st.moon_alt)
        image, mag = _image(st, d)
        images.append(image)
        if mag > mag_max:
            i_max, mag_max = i, mag

    # Maximum de l'eclipse: l'image la plus profonde, pas le milieu de C1-C4.
    # Le milieu n'est exact que si la Lune traversait le Soleil a vitesse
    # constante en ligne droite; et pour une totale, "l'obscuration la plus
    # forte" ne departagerait rien, toutes les images de la totalite valant 1.
    # La magnitude, elle, continue de croitre pendant la totalite.
    t_max = debut + i_max * PAS_S
    t_milieu = (contacts["c1"] + contacts["c4"]) / 2.0
    journal.append(f"    maximum a l'image {i_max} ({t_max - debut:.0f} s), "
                   f"milieu C1-C4 a {t_milieu - debut:.0f} s, "
                   f"ecart {t_max - t_milieu:+.0f} s")

    lisible = " ".join(
        f"{k}={'aucun' if v is None else _instant(ts, t_origine, v).utc_strftime('%H:%M:%S')}"
        for k, v in contacts.items())
    journal.append(f"    contacts UTC: {lisible}, "
                   f"maximum {_instant(ts, t_origine, t_max).utc_strftime('%H:%M:%S')}")

    t_max_jd = _instant(ts, t_origine, t_max)
    etoiles, catalogue_ok = etoiles_visibles(obs, t_max_jd)

    return {
        "id": site.id,
        "name_fr": site.name_fr, "name_en": site.name_en,
        "lat": site.lat, "lon": site.lon,
        "elevation_m": site.elevation_m, "tz": site.tz,
        # Secondes depuis t0_utc, et non des dates: c'est l'axe des images.
        "contacts": {k: (None if v is None else round(v - debut, 3))
                     for k, v in contacts.items()},
        # Meme axe que les contacts: l'instant qu'illustre `sky_at_max`, celui
        # vers lequel la page saute et que rend la route affiche.
        "t_max_s": round(t_max - debut, 3),
        "t0_utc": _instant(ts, t_origine, debut).utc_iso(), "step_s": PAS_S,
        "frames": images,
        "sky_at_max": {
            "planets": planetes_visibles(eph, obs, t_max_jd),
            "stars": etoiles[:ETOILES_MAX],
            "star_catalogue_available": catalogue_ok,
        },
    }


def main():
    eph, ts = open_ephemeris()
    journal = []
    sites = []
    for s in SITES:
        journal.append(f"  {s.id}:")
        sites.append(construire_site(eph, ts, s, journal))

    document = {
        "eclipse": {"id": "2026-08-12",
                    "label_fr": "Éclipse totale de Soleil du 12 août 2026",
                    "label_en": "Total solar eclipse of 12 August 2026"},
        "source": {"ephemeris": "DE440s", "software": f"skyfield {skyfield.__version__}"},
        "sites": sites,
    }

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")

    for s in sites:
        contacts = " ".join(
            f"{k}={'aucun' if v is None else format(v, '.1f')}"
            for k, v in s["contacts"].items())
        print(f"{s['id']}: {len(s['frames'])} images depuis {s['t0_utc']}, "
              f"pas {s['step_s']} s, contacts (s) {contacts}, "
              f"t_max_s={s['t_max_s']:.1f}")
    print("\n".join(journal))
    print(f"ecrit {SORTIE} ({SORTIE.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
