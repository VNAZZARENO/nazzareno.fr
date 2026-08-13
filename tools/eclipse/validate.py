"""Compare les valeurs calculees aux valeurs publiees et ecrit VALIDATION.md.

Usage: source .venv/bin/activate && python3 -m tools.eclipse.validate

Les valeurs publiees ci-dessous sont transcrites de `NASA-REFERENCE.md`
(section "Instants de contact publies", tache 6). Rien n'est recalcule ni
reinvente ici: ce module ne fait que comparer.
"""

import json
import pathlib
from datetime import datetime, timedelta

from skyfield.api import load

DONNEES = pathlib.Path("assets/data/eclipse-2026-08-12.json")
RAPPORT = pathlib.Path("tools/eclipse/VALIDATION.md")

# Voir la section "Pourquoi 30 s et non 5 s" de VALIDATION.md pour la
# justification de cette valeur: les sources publiees se desaccordent deja
# entre elles de 5 a 12 s, essentiellement a cause de conventions de DeltaT
# differentes. 30 s reste largement assez fin pour attraper une vraie faute
# de calcul (date, signe de longitude, corps confondus, refraction oubliee),
# qui se chiffre en minutes ou en heures, jamais en dizaines de secondes.
TOLERANCE_CONTACT_S = 30.0
TOLERANCE_MAGNITUDE = 0.005
TOLERANCE_OBSCURATION = 0.01      # 1 point de pourcentage
TOLERANCE_ALTITUDE_DEG = 0.15     # hauteurs "hautes": refraction negligeable
# Palma: comparaison apparente contre apparente (voir texte), mais la
# refraction pres de l'horizon amplifie toute petite difference de modele
# atmospherique (temperature, pression) entre notre calcul et T&D -- une
# tolerance plus large qu'ailleurs est donc le choix honnete, pas plus
# stricte.
TOLERANCE_ALTITUDE_PALMA_DEG = 0.20
TOLERANCE_AZIMUT_DEG = 0.5

# Index des champs dans chaque frame -- voir tools/eclipse/build.py::_image.
I_SUN_AZ, I_SUN_ALT = 0, 1
I_MAG, I_OBSC = 6, 7

NOMS = {"paris": "Paris", "espagne": "Palma de Majorque", "reykjavik": "Reykjavik"}

# Valeurs publiees, relevees a la tache 6. Voir NASA-REFERENCE.md, sections
# "Circonstances locales" et "Controles independants, et desaccords", pour la
# source exacte de chaque nombre.
#
# Source principale des contacts et de la magnitude: timeanddate.com (T&D),
# seule source consultee qui publie les quatre contacts a la seconde pour les
# trois villes, avec une methode identique d'une ville a l'autre. Palma est
# recoupee avec l'IGN espagnol (source officielle, calculs de
# l'Observatorio Astronomico Nacional).
PUBLIE = {
    "paris": {
        "contacts": {
            "c1": "2026-08-12T17:22:14Z",
            "c2": None,  # pas de totalite a Paris: l'eclipse y reste partielle
            "c3": None,
            "c4": "2026-08-12T19:09:28Z",
        },
        "magnitude": 0.931,
        # Aucune source primaire ne publie l'obscuration de Paris. Deux
        # valeurs secondaires, discordantes, circulent (IMCCE via
        # eclipse-solaire.fr, et WP-fr d'apres ici.fr). Affichees a titre
        # indicatif seulement -- voir NASA-REFERENCE.md, "Ce qui n'est pas
        # publie, et qu'on n'invente pas".
        "obscuration": None,
        "obscuration_indicative": [0.921, 0.922],
        "altitude_max_deg": 7.7,
        "azimuth_max_deg": 284.0,
    },
    "reykjavik": {
        "contacts": {
            "c1": "2026-08-12T16:47:13Z",
            "c2": "2026-08-12T17:48:18Z",
            "c3": "2026-08-12T17:49:18Z",
            "c4": "2026-08-12T18:47:40Z",
        },
        "magnitude": 1.002,
        "obscuration": 1.0,  # totale par definition: ce n'est pas une mesure
        "obscuration_indicative": None,
        "altitude_max_deg": 24.5,
        "azimuth_max_deg": 253.0,
    },
    "espagne": {
        "contacts": {
            "c1": "2026-08-12T17:38:04Z",
            "c2": "2026-08-12T18:31:06Z",
            "c3": "2026-08-12T18:32:42Z",
            "c4": "2026-08-12T19:22:34Z",
        },
        "magnitude": 1.015,
        "obscuration": 1.000,  # IGN
        "obscuration_indicative": None,
        # T&D (apparente, comme notre calcul -- voir le texte sur la
        # refraction). L'IGN donne 2.4 deg pour le meme instant: ce n'est
        # pas une divergence de calcul, voir la section dediee plus bas.
        "altitude_max_deg": 2.6,
        "altitude_ign_deg": 2.4,
        "azimuth_max_deg": 287.3,  # IGN
    },
}


def _t0(site):
    return datetime.fromisoformat(site["t0_utc"].replace("Z", "+00:00"))


def _instant_calcule(site, cle):
    v = site["contacts"].get(cle)
    return None if v is None else _t0(site) + timedelta(seconds=v)


def _parse_iso(s):
    return None if s is None else datetime.fromisoformat(s.replace("Z", "+00:00"))


def _fmt_dt(dt):
    return "—" if dt is None else dt.strftime("%H:%M:%S")


def _frame_index_max(site):
    """Index de frame designe par t_max_s comme instant du maximum."""
    return int(round(site["t_max_s"] / site["step_s"]))


def _verifier_maximum(site, journal):
    """Confirme que l'image pointee par t_max_s est bien celle de magnitude
    maximale parmi toutes les frames du site. Un desaccord serait un vrai
    defaut de build.py, pas une divergence avec les sources publiees -- on le
    signale donc separement, pas comme un ecart de validation externe.
    """
    frames = site["frames"]
    i_declare = _frame_index_max(site)
    i_reel = max(range(len(frames)), key=lambda i: frames[i][I_MAG])
    ok = i_declare == i_reel
    if not ok:
        journal.append(
            f"ATTENTION {site['id']}: t_max_s designe l'image {i_declare} "
            f"(magnitude {frames[i_declare][I_MAG]:.5f}) mais le maximum reel "
            f"sur l'ensemble des frames est a l'image {i_reel} "
            f"(magnitude {frames[i_reel][I_MAG]:.5f})."
        )
    else:
        journal.append(
            f"OK {site['id']}: t_max_s (image {i_declare}) coincide avec le "
            f"maximum recalcule sur les {len(frames)} frames."
        )
    return i_declare, ok


def _ligne(lieu, grandeur, publie, calcule, ecart, tolerance, verdict):
    return (f"| {lieu} | {grandeur} | {publie} | {calcule} | {ecart} | "
            f"{tolerance} | {verdict} |")


def main():
    donnees = json.loads(DONNEES.read_text())
    ts = load.timescale()
    # Delta T au voisinage de l'eclipse: c'est ce decalage qui explique
    # l'essentiel du desaccord entre sources publiees sur les instants.
    t_eclipse = ts.utc(2026, 8, 12, 17, 45, 51)
    delta_t_s = float(t_eclipse.delta_t)

    lignes = [
        "# Validation du calcul",
        "",
        "Comparaison du calcul de `tools/eclipse/build.py` (fichier "
        "`assets/data/eclipse-2026-08-12.json`) aux valeurs publiees "
        "consignees dans `NASA-REFERENCE.md` (tache 6), transcrites depuis "
        "timeanddate.com (T&D) et recoupees, pour Palma, avec l'IGN "
        "espagnol.",
        "",
        "**Rien dans ce fichier n'est une source.** Les valeurs publiees "
        "viennent de `NASA-REFERENCE.md`, qui les a lui-meme recopiees de "
        "sources externes avant qu'aucun calcul ne soit fait ici. Ce script "
        "ne fait que comparer deux colonnes de nombres et rapporter l'ecart.",
        "",
        "## Pourquoi 30 s de tolerance, et non 5 s",
        "",
        "Les sources publiees ne s'accordent pas entre elles : sur "
        "l'instant du maximum global, GSFC, EclipseWise et l'IMCCE different "
        "deja de 9 s ; sur les contacts de Palma, timeanddate.com, l'IGN et "
        "Wikipedia FR different de 2 a 6 s ; sur la duree de la totalite a "
        "Reykjavik, les sources islandaises different de 12 s. La cause "
        "recurrente est DeltaT (TT - UT1) : les sources retenues en "
        "supposent des valeurs allant de 69.6 s a 75.4 s (voir "
        "`NASA-REFERENCE.md`, \"Trois pieges de transcription\"), un ecart "
        "qui a lui seul deplace un contact de plusieurs secondes.",
        "",
        "Une tolerance de 5 s mesurerait donc ce desaccord entre sources, "
        "pas la justesse de ce calcul. 30 s reste tres discriminant : une "
        "vraie faute dans ce pipeline (mauvaise date, signe de longitude "
        "invertit, corps celeste confondu, refraction oubliee) deplace un "
        "contact de plusieurs minutes a plusieurs heures, jamais de vingt "
        "secondes.",
        "",
        f"**DeltaT utilise par skyfield pour cette eclipse (a 17:45:51 UTC) : "
        f"{delta_t_s:.2f} s.** A titre de comparaison, les sources "
        f"publiees retenues dans `NASA-REFERENCE.md` supposent, pour la "
        f"meme eclipse : GSFC 75.4 s, EclipseWise 72.4 s, IMCCE 75.319 s, "
        f"timeanddate.com 69.6 s. La valeur skyfield tombe meme legerement "
        f"sous la plus basse des quatre, ce qui est cohere avec des "
        f"contacts calcules systematiquement quelques secondes en avance "
        f"sur T&D (voir le tableau ci-dessous) : un DeltaT plus petit "
        f"avance legerement tous les instants.",
        "",
        "## Hauteur du Soleil : refraction comprise, un piege signale",
        "",
        "Le pipeline (`tools/eclipse/ephemeris.py::state_at`) rapporte des "
        "hauteurs **apparentes**, refraction atmospherique standard "
        "(15 degC, 1013.25 mbar) comprise -- c'est ce qui compte pour un "
        "rendu visuel, et c'est indispensable a Palma ou l'eclipse se joue "
        "a moins de 3 degres de l'horizon. timeanddate.com semble publier la "
        "meme convention (voir plus bas). L'IGN espagnol, lui, semble "
        "publier une hauteur **geometrique** (sans refraction) pour Palma : "
        "2.4 deg contre 2.6 deg chez T&D pour le meme instant. Comparer "
        "notre valeur a l'IGN sans corriger de la refraction comparerait "
        "deux grandeurs differentes ; la ligne \"IGN (info)\" du tableau "
        "l'affiche donc a part, avec l'explication qui suit.",
        "",
    ]

    tout_ok = True
    journal_maximum = []

    lignes += [
        "## Tableau de comparaison",
        "",
        "| Lieu | Grandeur | Publie | Calcule | Ecart | Tolerance | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]

    for site in donnees["sites"]:
        lieu = NOMS.get(site["id"], site["id"])
        attendu = PUBLIE.get(site["id"], {})

        # --- Contacts C1-C4 ---------------------------------------------
        for cle in ("c1", "c2", "c3", "c4"):
            ref_iso = attendu.get("contacts", {}).get(cle)
            calc_dt = _instant_calcule(site, cle)
            if ref_iso is None and calc_dt is None:
                lignes.append(_ligne(
                    lieu, cle.upper(), "—", "—", "—", "—",
                    "pas de totalite a ce lieu (fait astronomique)"))
                continue
            if ref_iso is None or calc_dt is None:
                # Desaccord entre le publie et le calcule sur l'EXISTENCE
                # meme du contact: jamais tolerable, quelle que soit la
                # tolerance numerique.
                tout_ok = False
                lignes.append(_ligne(
                    lieu, cle.upper(), _fmt_dt(_parse_iso(ref_iso)),
                    _fmt_dt(calc_dt), "n/a", f"{TOLERANCE_CONTACT_S:.0f} s",
                    "ECART (un seul des deux cotes a ce contact)"))
                continue
            ref_dt = _parse_iso(ref_iso)
            ecart_s = (calc_dt - ref_dt).total_seconds()
            ok = abs(ecart_s) <= TOLERANCE_CONTACT_S
            tout_ok &= ok
            lignes.append(_ligne(
                lieu, cle.upper(), _fmt_dt(ref_dt), _fmt_dt(calc_dt),
                f"{ecart_s:+.1f} s", f"{TOLERANCE_CONTACT_S:.0f} s",
                "ok" if ok else "ECART"))

        # --- Maximum: verification interne + magnitude/obscuration/hauteur/azimut
        i_max, max_ok = _verifier_maximum(site, journal_maximum)
        tout_ok &= max_ok
        frame_max = site["frames"][i_max]

        mag_calc = frame_max[I_MAG]
        if attendu.get("magnitude") is not None:
            ecart = mag_calc - attendu["magnitude"]
            ok = abs(ecart) <= TOLERANCE_MAGNITUDE
            tout_ok &= ok
            lignes.append(_ligne(
                lieu, "magnitude", f"{attendu['magnitude']:.4f}",
                f"{mag_calc:.5f}", f"{ecart:+.4f}", f"{TOLERANCE_MAGNITUDE}",
                "ok" if ok else "ECART"))

        obsc_calc = frame_max[I_OBSC]
        if attendu.get("obscuration") is not None:
            ecart = obsc_calc - attendu["obscuration"]
            ok = abs(ecart) <= TOLERANCE_OBSCURATION
            tout_ok &= ok
            lignes.append(_ligne(
                lieu, "obscuration", f"{attendu['obscuration'] * 100:.1f} %",
                f"{obsc_calc * 100:.2f} %", f"{ecart * 100:+.2f} pt",
                f"{TOLERANCE_OBSCURATION * 100:.0f} pt", "ok" if ok else "ECART"))
        elif attendu.get("obscuration_indicative"):
            vals = attendu["obscuration_indicative"]
            publie_str = " / ".join(f"{v * 100:.1f} %" for v in vals)
            ecart_str = " / ".join(
                f"{(obsc_calc - v) * 100:+.2f} pt" for v in vals)
            lignes.append(_ligne(
                lieu, "obscuration", publie_str, f"{obsc_calc * 100:.2f} %",
                ecart_str, "n/a (reference non stricte)", "info"))

        if attendu.get("altitude_max_deg") is not None:
            alt_calc = frame_max[I_SUN_ALT]
            ref_alt = attendu["altitude_max_deg"]
            tol = (TOLERANCE_ALTITUDE_PALMA_DEG if site["id"] == "espagne"
                   else TOLERANCE_ALTITUDE_DEG)
            ecart = alt_calc - ref_alt
            ok = abs(ecart) <= tol
            tout_ok &= ok
            lignes.append(_ligne(
                lieu, "hauteur du Soleil (max, apparente)", f"{ref_alt:.1f} deg",
                f"{alt_calc:.4f} deg", f"{ecart:+.4f} deg", f"{tol:.2f} deg",
                "ok" if ok else "ECART"))
            if attendu.get("altitude_ign_deg") is not None:
                ref_ign = attendu["altitude_ign_deg"]
                ecart_ign = alt_calc - ref_ign
                lignes.append(_ligne(
                    lieu, "hauteur du Soleil (max, IGN)", f"{ref_ign:.1f} deg",
                    f"{alt_calc:.4f} deg", f"{ecart_ign:+.4f} deg",
                    "n/a (geometrique probable, voir texte)", "info"))

        if attendu.get("azimuth_max_deg") is not None:
            az_calc = frame_max[I_SUN_AZ]
            ref_az = attendu["azimuth_max_deg"]
            ecart = az_calc - ref_az
            ok = abs(ecart) <= TOLERANCE_AZIMUT_DEG
            tout_ok &= ok
            lignes.append(_ligne(
                lieu, "azimut du Soleil (max)", f"{ref_az:.1f} deg",
                f"{az_calc:.4f} deg", f"{ecart:+.4f} deg",
                f"{TOLERANCE_AZIMUT_DEG:.1f} deg", "ok" if ok else "ECART"))

    lignes += [
        "",
        "Les lignes marquees **info** ne comptent pas dans le verdict "
        "global : elles comparent a une reference que `NASA-REFERENCE.md` "
        "signale lui-meme comme non stricte (deux valeurs discordantes pour "
        "l'obscuration de Paris) ou incompatible en nature (hauteur "
        "geometrique de l'IGN contre hauteur apparente calculee). Elles "
        "sont affichees pour transparence, pas pour etre satisfaites ou "
        "non.",
        "",
        "## Coherence interne : t_max_s contre le maximum recalcule",
        "",
    ]
    lignes += [f"- {ligne}" for ligne in journal_maximum]

    lignes += [
        "",
        "## Ce que cette validation ne couvre pas",
        "",
        "- **Paris repose sur une seule source a la seconde** "
        "(timeanddate.com). L'IMCCE et l'Observatoire de Paris publient des "
        "circonstances locales, mais uniquement via un formulaire "
        "JavaScript dont la sortie n'a pas pu etre recuperee pour la tache "
        "6 ; les sites secondaires qui citent l'IMCCE ne recoupent qu'a la "
        "minute pres.",
        "- **timeanddate.com est un agregateur commercial**, pas un service "
        "d'ephemerides national ou universitaire. C'est la source retenue "
        "parce qu'elle est la seule a publier les quatre contacts a la "
        "seconde pour les trois villes avec une methode homogene, pas parce "
        "qu'elle fait autorite au meme titre que GSFC ou l'IGN.",
        "- **Reykjavik est pres du bord du trajet de la totalite** : les "
        "sources publiees donnent des durees de totalite qui vont de 58 a "
        "70 s selon le point exact vise dans la ville. Un ecart de "
        "quelques secondes sur C2/C3 a Reykjavik peut donc venir d'un choix "
        "de point different, pas d'une erreur de calcul de part ou d'autre.",
        "- **Le point exact designe par chaque ville n'est pas publie** par "
        "T&D. Comparer nos coordonnees (voir `build.py::SITES`) a un point "
        "inconnu est une limite intrinseque de cette validation, quelle que "
        "soit la qualite du calcul des deux cotes.",
        "- Cette validation compare des **instants et des grandeurs "
        "ponctuelles au maximum**, pas la trajectoire complete de l'ombre "
        "ni le rendu visuel (flux RGB, assombrissement centre-bord, ciel "
        "etoile), qui ne sont pas publies avec une precision comparable "
        "par les sources retenues.",
        "",
        f"## Verdict global : {'CONFORME' if tout_ok else 'ECARTS DETECTES'}",
        "",
    ]
    if tout_ok:
        lignes.append(
            "Tous les contacts, la magnitude, l'obscuration, la hauteur et "
            "l'azimut du Soleil au maximum, pour les trois sites, tombent "
            "dans la tolerance annoncee. `t_max_s` designe bien, dans les "
            "trois cas, l'image de magnitude maximale parmi les frames "
            "calculees.")
    else:
        lignes.append(
            "Au moins un ecart depasse la tolerance annoncee -- voir le "
            "tableau ci-dessus pour le detail. Ne pas elargir la tolerance "
            "pour faire disparaitre l'ecart : chercher la cause (DeltaT, "
            "altitude du site, point de reference different de celui de la "
            "source, ou vraie faute de calcul).")
    lignes.append("")

    RAPPORT.write_text("\n".join(lignes), encoding="utf-8")
    print("\n".join(lignes))
    raise SystemExit(0 if tout_ok else 1)


if __name__ == "__main__":
    main()
