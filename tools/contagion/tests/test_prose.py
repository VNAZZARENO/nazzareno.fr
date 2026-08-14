# tools/contagion/tests/test_prose.py
"""La prose tient les regles du site, et ses nombres sortent du calcul."""
import json
import pathlib
import re
import statistics

import pytest

from tools.contagion.figures import (EPISODES, PAGES, _moyenne_fenetre,
                                     calculer, nombre)
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation

RACINE = pathlib.Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def pages():
    return {lang: chemin.read_text(encoding="utf-8") for lang, chemin in PAGES.items()}


@pytest.fixture(scope="module")
def ctx():
    return calculer()


def test_plus_aucun_premier_jet(pages):
    for lang, texte in pages.items():
        assert "⟨" not in texte and "⟩" not in texte, lang


def test_pas_de_tiret_cadratin(pages):
    for lang, texte in pages.items():
        assert "—" not in texte, lang


def test_espace_insecable_avant_pourcent(pages):
    corps = re.sub(r"<svg.*?</svg>", "", pages["fr"], flags=re.S)
    assert not re.search(r"\d %", corps), "espace secable avant % dans la prose fr"


def test_la_correlation_pleine_periode_citee_est_la_bonne(pages, ctx):
    for lang, texte in pages.items():
        attendu = nombre(ctx["rho_pleine"], lang, 2)
        assert attendu in texte, f"{lang}: rho pleine periode {attendu} absent"


def test_le_controle_sans_lissage_est_le_bon(pages):
    dates, rx, ry = charger_cloture(ma2=False)
    brut = correlation(rx, ry)
    for lang, texte in pages.items():
        attendu = nombre(brut, lang, 2)
        assert attendu in texte, f"{lang}: controle jour simple {attendu} absent"


def test_le_noscript_cite_les_fixtures(pages):
    fixture = json.loads(
        (RACINE / "tools" / "js-tests" / "fixture-contagion.json").read_text())
    cas = next(c for c in fixture["cas"] if c["q"] == 0.9)
    for lang, texte in pages.items():
        for valeur in (cas["rho"], cas["rho_corrigee"]):
            assert nombre(valeur, lang, 3) in texte, (lang, valeur)


def test_les_moyennes_d_episode_citees_sont_les_bonnes(pages, ctx):
    g = ctx["glissante"]
    for lang, texte in pages.items():
        for episode in EPISODES:
            for serie in ("brute", "corrigee"):
                attendu = nombre(_moyenne_fenetre(g["dates"], g[serie], *episode),
                                 lang, 2)
                assert attendu in texte, (lang, episode, serie)


MOIS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}


def _date_en_prose(iso, lang):
    an, mois, jour = iso.split("-")
    jour = str(int(jour))
    if lang == "fr" and jour == "1":
        jour = "1er"
    return f"{jour} {MOIS[lang][int(mois) - 1]} {an}"


def test_le_nombre_de_jours_et_les_bornes_viennent_du_manifeste(pages, ctx):
    meta = json.loads(
        (RACINE / "assets" / "data" / "contagion.json").read_text())["meta"]
    assert meta["n"] == len(ctx["rx"])
    for lang, texte in pages.items():
        assert str(meta["n"]) in texte, f"{lang}: n={meta['n']} absent"
        for borne in (meta["debut"], meta["fin"]):
            attendu = _date_en_prose(borne, lang)
            assert attendu in texte, f"{lang}: borne {attendu} absente"


def test_les_deciles_cites_sont_les_bons(pages, ctx):
    reels = ctx["tranches_reelles"]
    simules = ctx["tranches_simulees"]
    for lang, texte in pages.items():
        # La montee brute du constat, premier et dernier decile reels.
        for valeur in (reels[0]["rho"], reels[-1]["rho"]):
            assert nombre(valeur, lang, 2) in texte, (lang, valeur)
        # La meme montee dans le monde simule.
        for valeur in (simules[0]["rho"], simules[-1]["rho"]):
            assert nombre(valeur, lang, 2) in texte, (lang, valeur)
        # Le premier decile corrige et son intervalle: le point qui ne dit rien.
        for cle in ("rho_corrigee", "ic_corr_bas", "ic_corr_haut"):
            assert nombre(reels[0][cle], lang, 2) in texte, (lang, cle, 1)
        # Le dernier decile corrige, son intervalle, son delta: le fait narre.
        for cle in ("rho_corrigee", "ic_corr_bas", "ic_corr_haut"):
            assert nombre(reels[-1][cle], lang, 2) in texte, (lang, cle, 10)
        assert nombre(reels[-1]["delta"], lang, 1) in texte, (lang, "delta", 10)


def test_le_maximum_glissant_cite_est_le_bon(pages, ctx):
    attendu_max = max(ctx["glissante"]["brute"])
    for lang, texte in pages.items():
        assert nombre(attendu_max, lang, 2) in texte, lang


def _acf1(s):
    n = len(s)
    m = sum(s) / n
    num = sum((s[i] - m) * (s[i + 1] - m) for i in range(n - 1))
    den = sum((v - m) ** 2 for v in s)
    return num / den


def test_les_statistiques_de_fenetre_citees_sont_les_bonnes(pages, ctx):
    """Le paragraphe qui refuse de sur-lire les moyennes d'episode cite quatre
    nombres: chacun doit sortir du calcul, pas du clavier."""
    g = ctx["glissante"]
    d08, f08 = EPISODES[0]
    d20, f20 = EPISODES[1]
    fenetres_2008 = [i for i, d in enumerate(g["dates"]) if d08 <= d <= f08]
    from tools.contagion import rolling
    brute, corrigee, delta = rolling.glissantes(ctx["rx"], ctx["ry"], fenetre=60)
    delta_median_2008 = statistics.median(delta[i] for i in fenetres_2008)
    corr_2020 = [c for d, c in zip(g["dates"], g["corrigee"]) if d20 <= d <= f20]
    au_dessus = sum(1 for c in corr_2020 if c > ctx["rho_pleine"])
    autocorr = _acf1(ctx["rx"])
    n_effectif = round(60 * (1 - autocorr) / (1 + autocorr))
    for lang, texte in pages.items():
        assert str(len(fenetres_2008)) in texte, (lang, "fenetres 2008")
        assert nombre(delta_median_2008, lang, 1) in texte, (lang, "delta 2008")
        assert nombre(statistics.pstdev(corr_2020), lang, 2) in texte, (lang, "sd 2020")
        liaison = " des " if lang == "fr" else " of the "
        assert f"{au_dessus}{liaison}{len(corr_2020)}" in texte, (lang, "au-dessus")
        assert nombre(autocorr, lang, 2) in texte, (lang, "autocorrelation")
        assert str(n_effectif) in texte, (lang, "n effectif")
