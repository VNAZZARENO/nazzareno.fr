"""Les figures affirment des choses; ce fichier les verifie.

Une figure fausse est pire qu'une figure absente: elle a l'air d'une preuve.
Les tests portent donc sur les trois affirmations que les legendes ecrivent en
toutes lettres, plus sur le fait que le trace ne sort pas de son cadre.
"""

import math

from tools.eclipse import figures, limb


def _serie():
    # Rayons apparents reels de Paris au maximum du 12 aout 2026. Les memes que
    # ceux du fichier de donnees, a la sixieme decimale.
    return figures.serie(0.262960, 0.271866)


def test_serie_va_de_zero_a_la_totalite():
    points = _serie()
    assert points[0][0] == 0.0            # disques disjoints: rien de couvert
    assert points[0][1] == 1.0            # donc tout le flux
    assert points[-1][0] > 0.9999         # disques concentriques: tout couvert
    assert points[-1][1] < 1e-9           # et plus rien du flux


def test_obscuration_croit_et_le_flux_decroit():
    """Les deux monotonies sont ce qui autorise a lire la courbe de gauche a
    droite. Si l'une se cassait, la figure resterait jolie et mentirait."""
    points = _serie()
    for (o1, y1, *_), (o2, y2, *_) in zip(points, points[1:]):
        assert o2 >= o1 - 1e-12
        assert y2 <= y1 + 1e-12


def test_croisement_tombe_bien_vers_33_pour_cent():
    """L'affirmation centrale de la premiere figure ET de la prose."""
    o = figures.croisement(_serie())
    assert 0.32 < o < 0.35


def test_le_flux_passe_au_dessus_puis_au_dessous_du_disque_uniforme():
    points = _serie()
    avant = figures.au_plus_pres(points, 0.10)
    apres = figures.au_plus_pres(points, 0.92)
    assert avant[1] > 1.0 - avant[0]      # il reste PLUS de lumiere
    assert apres[1] < 1.0 - apres[0]      # il en reste MOINS


def test_le_rouge_finit_par_l_emporter_sur_le_bleu():
    """Deuxieme figure: le limbe est plus sombre dans le bleu, donc le flux
    restant se rechauffe quand la Lune couvre le centre. Et le creux sous 1 au
    debut est reel, pas un artefact de trace."""
    points = _serie()
    _, _, r_debut, b_debut = figures.au_plus_pres(points, 0.25)
    _, _, r_fin, b_fin = figures.au_plus_pres(points, 0.92)
    assert r_debut / b_debut < 1.0
    assert r_fin / b_fin > 1.10


def test_lstar_est_toujours_au_dessus_du_flux():
    """Troisieme figure: c'est l'ecart entre les deux courbes qui porte tout
    l'argument. S'il s'annulait ou changeait de signe, la figure ne dirait plus
    rien."""
    for y in (0.01, 0.05, 0.2, 0.5, 0.9):
        assert figures.lstar(y) > y
    assert figures.lstar(0.0) == 0.0
    assert math.isclose(figures.lstar(1.0), 1.0, abs_tol=1e-12)


def test_lstar_au_maximum_parisien():
    """Le nombre cite dans la legende et dans la liste d'honnetete."""
    assert 0.27 < figures.lstar(0.0545) < 0.29


def test_le_trace_reste_dans_son_panneau():
    """Un point hors cadre ne leve aucune erreur en SVG: il sort du dessin,
    silencieusement. On verifie donc les bornes a la main."""
    p = figures.Panneau(30, 300, 0.0, 1.0, (0.0, 1.0), str)
    assert p.y(0.0) == 300
    assert p.y(1.0) == 30
    for o, y, *_ in _serie():
        assert 30 <= p.y(y) <= 300
        assert figures.X0 <= figures.px(o) <= figures.X1


def test_les_pourcentages_francais_portent_l_espace_insecable():
    """Regle typographique, et regression facile: un espace ordinaire laisserait
    le % passer seul a la ligne."""
    assert figures.pourcent(33.3, "fr", 1) == "33,3 %"
    assert figures.pourcent(33.3, "en", 1) == "33.3%"


def test_les_differences_sont_en_points_et_signees():
    # espace insecable avant l'unite comme avant le %, pour que "pt" ne parte
    # jamais seul a la ligne
    assert figures.points_pct(1.4, "fr", 1) == "+1,4\u00a0pt"
    assert figures.points_pct(-3.6, "fr", 1) == "\u22123,6\u00a0pt"


def test_aucun_tiret_cadratin_dans_les_textes_produits():
    """Consigne d'ecriture de la page: pas un seul tiret cadratin."""
    for table in (figures.TEXTES_1, figures.TEXTES_2, figures.TEXTES_3,
                  figures.TEXTES_D):
        assert "—" not in repr(table)


def test_le_champ_de_l_encart_est_celui_du_shader():
    """La legende des trois disques annonce un cadrage. Si CHAMP_DEG bougeait
    dans inset.glsl.js sans bouger ici, elle annoncerait un champ que les images
    n'ont pas."""
    source = (figures.RACINE / "assets" / "js" / "eclipse" / "inset.glsl.js").read_text(
        encoding="utf-8")
    assert f"export const CHAMP_DEG = {figures.CHAMP_DEG};" in source


def test_le_modele_de_flux_est_bien_celui_de_la_page():
    """figures.py ne doit pas avoir sa propre copie de la loi d'assombrissement:
    une seconde table finirait par diverger de celle du fichier de donnees. On
    rejoue donc un echantillon a la MEME separation et on compare."""
    r_sun, r_moon = 0.262960, 0.271866
    points = _serie()
    i = figures.N_POINTS // 2
    d = (r_sun + r_moon) * (1.0 - i / figures.N_POINTS)
    attendu = limb.rgb_flux_fraction(d, r_sun, r_moon, n=figures.ANNEAUX)
    _, _, r, b = points[i]
    assert math.isclose(r, attendu[0], rel_tol=1e-12)
    assert math.isclose(b, attendu[2], rel_tol=1e-12)
