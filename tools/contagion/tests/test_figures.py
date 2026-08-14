# tools/contagion/tests/test_figures.py
"""Ce que les legendes affirment, un test par affirmation."""
import pytest

from tools.contagion import figures


@pytest.fixture(scope="module")
def contexte():
    return figures.calculer()          # un seul calcul pour tous les tests


def test_fig1_courbe_monte(contexte):
    bruts = [t["rho"] for t in contexte["tranches_reelles"]]
    assert bruts[-1] - bruts[0] > 0.25


def test_fig1_svg_bien_forme(contexte):
    svg = figures.fig_constat(contexte, "fr")
    assert svg.count("<svg") == svg.count("</svg>") == 1
    assert 'role="img"' in svg and "aria-labelledby" in svg
    assert "<details" in svg and "<table" in svg


def test_nombres_francais(contexte):
    assert figures.nombre(0.5812, "fr", 2) == "0,58"
    assert figures.nombre(0.5812, "en", 2) == "0.58"
    # MEME convention que tools/eclipse/figures.py, verifiee sur ses octets:
    # espace insecable U+00A0 avant % en francais, rien du tout en anglais.
    assert figures.pourcent(92.123, "fr", 1) == "92,1 %"
    assert figures.pourcent(92.123, "en", 1) == "92.1%"


def test_pas_de_tiret_cadratin(contexte):
    for lang in ("fr", "en"):
        assert "—" not in figures.fig_constat(contexte, lang)


def test_moins_typographique(contexte):
    # MEME convention que points_pct de l'eclipse: U+2212 pour le signe moins,
    # jamais le trait d'union ASCII.
    assert figures.nombre(-1.0, "fr", 2) == "−1,00"
    assert figures.nombre(-0.5, "en", 2) == "−0.50"
    svg = figures.fig_constat(contexte, "fr")
    assert ">-" not in svg.replace("><", ">\n<")


def test_fig1_serie_et_repere_etiquetes(contexte):
    # l'identite d'un trace ne repose jamais sur la seule couleur: chaque
    # serie ET la droite de reference portent un mot pose au contact.
    svg_fr = figures.fig_constat(contexte, "fr")
    assert "pleine période" in svg_fr and "brute" in svg_fr
    svg_en = figures.fig_constat(contexte, "en")
    assert "full sample" in svg_en and "raw" in svg_en


def test_fig2_le_monde_constant_monte_aussi(contexte):
    simulees = [t["rho"] for t in contexte["tranches_simulees"]]
    assert simulees[-1] - simulees[0] > 0.25


def test_fig2_analytique_colle_au_monte_carlo(contexte):
    from tools.contagion.bias import rho_conditionnelle
    for t in contexte["tranches_simulees"]:
        attendu = rho_conditionnelle(contexte["rho_pleine"], t["delta"])
        assert t["ic_bas"] < attendu < t["ic_haut"], "la formule sort de l'IC bootstrap"


def test_fig2_un_monde_sans_unite(contexte):
    # le monde simule est un couple gaussien SANS unite: son axe ne pretend
    # pas etre le rendement S&P, et ses amplitudes ne sont pas des pourcents.
    for lang, interdit in (("fr", "rendement S&P"), ("en", "S&P return")):
        html = figures.fig_retournement(contexte, lang)
        assert interdit not in html
        assert "%" not in html


def test_fig2_formule_dans_le_tableau(contexte):
    # toute figure existe aussi sous forme de nombres: la prediction tracee
    # doit avoir sa colonne dans la vue tabulaire.
    assert "Formule" in figures.fig_retournement(contexte, "fr")
    assert "Formula" in figures.fig_retournement(contexte, "en")


def test_fig3_la_corrigee_tient_ou_l_estimateur_tient(contexte):
    # meme lecon que test_deciles: l'inversion F-R amplifie le bruit ~1/sqrt(1+delta)
    # dans les deciles bas; la platitude ne s'affirme que sur les deciles 3 a 10.
    bruts = [t["rho"] for t in contexte["tranches_reelles"]]
    corriges_serres = [t["rho_corrigee"] for t in contexte["tranches_reelles"][2:]]
    ecart = max(abs(c - contexte["rho_pleine"]) for c in corriges_serres)
    assert ecart < (bruts[-1] - bruts[0]) / 3


# La MEME constante que la figure: une derive des bornes ferait passer les
# tests sur d'autres episodes que ceux des bandes tracees.
EPISODES_TEST = figures.EPISODES


def _moyenne_episode(ctx, serie, debut, fin):
    g = ctx["glissante"]
    valeurs = [v for d, v in zip(g["dates"], g[serie]) if debut <= d <= fin]
    assert len(valeurs) > 20, "episode absent des donnees"
    return sum(valeurs) / len(valeurs)


def test_fig4_la_brute_monte_dans_les_deux_crises(contexte):
    for debut, fin in EPISODES_TEST:
        assert _moyenne_episode(contexte, "brute", debut, fin) > \
            contexte["rho_pleine"] + 0.1


def test_fig4_la_correction_reduit_l_exces(contexte):
    for debut, fin in EPISODES_TEST:
        exces_brut = _moyenne_episode(contexte, "brute", debut, fin) - contexte["rho_pleine"]
        exces_corrige = _moyenne_episode(contexte, "corrigee", debut, fin) - contexte["rho_pleine"]
        assert exces_corrige < exces_brut, (debut, "la correction n'a rien reduit")
        # PAS d'assertion exces_corrige ~ 0: ce qui reste est le contenu de la page,
        # la legende citera la valeur qui sort, quelle qu'elle soit


def test_fig4_svg_bien_forme(contexte):
    for lang in ("fr", "en"):
        svg = figures.fig_reste(contexte, lang)
        assert svg.count("<svg") == 1 and "aria-labelledby" in svg
        assert svg.count('class="fig-episode"') == 2
        assert "—" not in svg


def test_fig2_fig3_svg_bien_formes_et_etiquetes(contexte):
    for fabrique in (figures.fig_retournement, figures.fig_correction):
        for lang in ("fr", "en"):
            svg = fabrique(contexte, lang)
            assert svg.count("<svg") == 1 and "aria-labelledby" in svg
            assert "—" not in svg
    # les identites de serie ne reposent jamais sur la seule couleur:
    # chaque serie porte une etiquette posee au contact (doctrine eclipse)
    svg_fr = figures.fig_correction(contexte, "fr")
    assert "brute" in svg_fr and "corrigée" in svg_fr
    svg2_fr = figures.fig_retournement(contexte, "fr")
    assert "Monte-Carlo" in svg2_fr and "formule" in svg2_fr
