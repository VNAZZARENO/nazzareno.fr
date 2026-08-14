# tools/contagion/figures.py
"""Les quatre figures SVG de la page contagion, calculees puis injectees.

Meme doctrine que tools/eclipse/figures.py, dont ce module reprend les
conventions (SVG en ligne pour heriter des deux themes, vue tabulaire sous
<details>, injection entre reperes, aucune valeur saisie a la main). Les
couleurs de serie prolongent le choix valide de l'eclipse: l'accent vert du
site tombe sous le plancher de chroma des qu'il porte une courbe, donc la
serie A reprend le vert de .fig-svg (--serie-a) et la serie B est un bleu
passe au meme validateur de palette, cinq controles sur les DEUX fonds.
"""
import bisect
import pathlib
import re

from tools.contagion import rolling
from tools.contagion.deciles import par_deciles
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation, tirages
from tools.contagion.bias import rho_conditionnelle

RACINE = pathlib.Path(__file__).resolve().parents[2]
PAGES = {
    "fr": RACINE / "projets" / "contagion.html",
    "en": RACINE / "en" / "projects" / "contagion.html",
}
GRAINE = 20260814

# Geometrie commune: viewBox 640 de large, zone de trace x dans [54, 528],
# memes marges que les figures de l'eclipse pour que l'oeil retrouve la grille.
X0, X1 = 54.0, 528.0
# Couleurs: les DEUX classes CSS de serie (.fig-serie-a, .fig-serie-b dans
# style.css); pas de couleur en dur ici.


def echapper(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nombre(x, lang, dec):
    """Signe moins typographique U+2212, jamais le trait d'union ASCII:
    MEME convention que points_pct dans tools/eclipse/figures.py."""
    s = f"{x:.{dec}f}".replace("-", "−")
    return s.replace(".", ",") if lang == "fr" else s


def pourcent(x, lang, dec):
    """Espace insecable (U+00A0) avant % en francais, rien en anglais.

    MEME caractere que tools/eclipse/figures.py: une seule convention sur le site.
    """
    return (f"{nombre(x, lang, dec)} %" if lang == "fr"
            else f"{nombre(x, lang, dec)}%")


def sx(v, v0, v1):
    """Abscisse SVG d'une valeur v sur [v0, v1]."""
    return round(X0 + (v - v0) / (v1 - v0) * (X1 - X0), 2)


def sy(v, v0, v1, y0, y1):
    """Ordonnee SVG (axe inverse) d'une valeur v sur [v0, v1] trace entre y0 et y1."""
    return round(y1 - (v - v0) / (v1 - v0) * (y1 - y0), 2)


def calculer():
    """Tout le calcul des quatre figures, une seule fois."""
    dates, rx, ry = charger_cloture()
    rho_pleine = correlation(rx, ry)
    tranches_reelles = par_deciles(rx, ry, graine_bootstrap=GRAINE)
    xs, ys = tirages(rho_pleine, len(rx), GRAINE)
    tranches_simulees = par_deciles(xs, ys, graine_bootstrap=GRAINE)
    brute, corrigee, delta = rolling.glissantes(rx, ry, fenetre=60)
    return {
        "dates": dates, "rx": rx, "ry": ry, "rho_pleine": rho_pleine,
        "tranches_reelles": tranches_reelles,
        "tranches_simulees": tranches_simulees,
        "glissante": {"dates": dates[59:], "brute": brute, "corrigee": corrigee},
    }


def _etiquette(x, y, texte):
    """Nom de serie pose AU CONTACT de son trace, a l'encre (classe fig-serie):
    l'identite d'un trace ne repose jamais sur la seule couleur. MEME mecanisme
    que Panneau.etiquette dans tools/eclipse/figures.py; la marge droite de
    112 px du cadre existe exactement pour ces mots."""
    return (f'<text class="fig-serie" x="{round(x, 2)}" y="{round(y, 2)}">'
            f'{echapper(texte)}</text>')


def _tranches_svg(tranches, rho_reference, lang, id_fig, titre, description,
                  etiquettes, avec_corrigee=False, courbe_analytique=None,
                  simule=False):
    """Le rendu commun aux figures 1 a 3: deciles en x, correlation en y.

    etiquettes: dict cle -> (texte, decalage_dy) pour "a", "reference" et,
    selon la figure, "b" ou "analytique"; chaque texte est pose dans la marge
    droite a la hauteur du dernier point du trace qu'il nomme.
    avec_corrigee: si vrai, trace aussi rho_corrigee et son IC par decile
    (figure 3, la serie corrigee).
    courbe_analytique: liste de valeurs par decile a tracer en trait continu
    (figure 2, la prediction de la formule).
    simule: le monde temoin est un couple gaussien SANS unite; son axe ne
    pretend pas etre le rendement S&P et ses amplitudes ne sont pas des
    pourcents (figure 2).
    """
    y0, y1 = 32.0, 320.0
    v0, v1 = 0.0, 1.0
    xs_dec = [sx(i + 0.5, 0, 10) for i in range(10)]
    # Deux series de points: ecart symetrique de 3 px de part et d'autre du
    # centre du decile; c'est l'anneau couleur papier des disques qui garde
    # les deux series separables meme quand les valeurs se confondent
    # presque (decile 8).
    dx_a = -3.0 if avec_corrigee else 0.0
    parts = [f'<figure class="fig" id="{id_fig}">']
    parts.append(f'<svg class="fig-svg" viewBox="0 0 640 388" role="img" '
                 f'aria-labelledby="{id_fig}-t {id_fig}-d">')
    parts.append(f'<title id="{id_fig}-t">{echapper(titre)}</title>')
    parts.append(f'<desc id="{id_fig}-d">{echapper(description)}</desc>')
    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = sy(v, v0, v1, y0, y1)
        parts.append(f'<line class="fig-grille" x1="{X0}" y1="{y}" x2="{X1}" y2="{y}"/>')
        parts.append(f'<text class="fig-tick fig-tick-y" x="{X0 - 8}" y="{y + 4}">'
                     f'{nombre(v, lang, 2)}</text>')
    yref = sy(rho_reference, v0, v1, y0, y1)
    parts.append(f'<polyline class="fig-repere" points="{X0},{yref} {X1},{yref}"/>')
    if courbe_analytique is not None:
        pts = " ".join(f"{x},{sy(v, v0, v1, y0, y1)}"
                       for x, v in zip(xs_dec, courbe_analytique))
        parts.append(f'<polyline class="fig-trait fig-serie-b" points="{pts}"/>')
    for x, t in zip(xs_dec, tranches):
        ybas, yhaut = sy(t["ic_bas"], v0, v1, y0, y1), sy(t["ic_haut"], v0, v1, y0, y1)
        parts.append(f'<line class="fig-ic fig-serie-a" x1="{x + dx_a}" y1="{ybas}" '
                     f'x2="{x + dx_a}" y2="{yhaut}"/>')
        parts.append(f'<circle class="fig-point fig-serie-a" cx="{x + dx_a}" '
                     f'cy="{sy(t["rho"], v0, v1, y0, y1)}" r="4"/>')
    if avec_corrigee:
        for x, t in zip(xs_dec, tranches):
            ybas = sy(t["ic_corr_bas"], v0, v1, y0, y1)
            yhaut = sy(t["ic_corr_haut"], v0, v1, y0, y1)
            parts.append(f'<line class="fig-ic fig-serie-b" x1="{x + 3}" y1="{ybas}" '
                         f'x2="{x + 3}" y2="{yhaut}"/>')
            parts.append(f'<circle class="fig-point fig-serie-b" cx="{x + 3}" '
                         f'cy="{sy(t["rho_corrigee"], v0, v1, y0, y1)}" r="4"/>')
    # Les etiquettes, dans la marge droite: a hauteur du dernier point pour
    # les series, a hauteur de la droite pour la reference (posee apres le
    # bout de la ligne, qui court jusqu'a X1).
    x_et = xs_dec[-1] + 13.0
    texte, dy = etiquettes["a"]
    parts.append(_etiquette(x_et, sy(tranches[-1]["rho"], v0, v1, y0, y1) + dy, texte))
    if avec_corrigee and "b" in etiquettes:
        texte, dy = etiquettes["b"]
        parts.append(_etiquette(
            x_et, sy(tranches[-1]["rho_corrigee"], v0, v1, y0, y1) + dy, texte))
    if courbe_analytique is not None and "analytique" in etiquettes:
        texte, dy = etiquettes["analytique"]
        parts.append(_etiquette(
            x_et, sy(courbe_analytique[-1], v0, v1, y0, y1) + dy, texte))
    texte, dy = etiquettes["reference"]
    parts.append(_etiquette(X1 + 6.0, yref + dy, texte))
    for i, t in enumerate(tranches):
        parts.append(f'<text class="fig-tick" x="{xs_dec[i]}" y="{y1 + 18}" '
                     f'text-anchor="middle">{i + 1}</text>')
    for i in (0, 4, 9):
        ampl = _amplitude(tranches[i]["amplitude_mediane"], lang, simule)
        parts.append(f'<text class="fig-tick" x="{xs_dec[i]}" y="{y1 + 34}" '
                     f'text-anchor="middle">{echapper(ampl)}</text>')
    if simule:
        axe = ("décile de |x| simulé, amplitude médiane en dessous" if lang == "fr"
               else "decile of simulated |x|, median magnitude below")
    else:
        axe = ("décile de |rendement S&P|, amplitude médiane en dessous"
               if lang == "fr" else "decile of |S&P return|, median magnitude below")
    parts.append(f'<text class="fig-tick" x="{(X0 + X1) / 2}" y="{y1 + 52}" '
                 f'text-anchor="middle">{echapper(axe)}</text>')
    parts.append("</svg>")
    parts.append(_tableau(tranches, lang, avec_corrigee=avec_corrigee,
                          analytique=courbe_analytique, simule=simule))
    parts.append("</figure>")
    return "\n".join(parts)


def _amplitude(v, lang, simule):
    """L'amplitude mediane d'un decile: en pourcent pour les rendements reels,
    en valeur nue pour le monde simule qui n'a pas d'unite."""
    return nombre(v, lang, 2) if simule else pourcent(v * 100, lang, 2)


def _scroller(resume):
    """Le conteneur qui defile: meme motif que la table des contacts de
    l'eclipse (tabindex pour le clavier, la page ne defile jamais)."""
    return (f'<div class="scroller" tabindex="0" role="region" '
            f'aria-label="{echapper(resume)}">\n')


def _tableau(tranches, lang, avec_corrigee, analytique=None, simule=False):
    """Vue tabulaire de la figure, repliee sous <details>: memes classes que
    les tableaux de figures de l'eclipse, sans une ligne de JavaScript.

    analytique: si la figure trace la prediction de la formule, elle doit
    aussi exister en nombres, donc en colonne (toute figure existe en tableau).
    """
    resume = "les valeurs des tracés" if lang == "fr" else "the plotted values"
    entetes = (["Décile", "n", "Amplitude médiane", "δ", "Corrélation"]
               if lang == "fr" else
               ["Decile", "n", "Median magnitude", "δ", "Correlation"])
    if avec_corrigee:
        entetes.append("Corrigée" if lang == "fr" else "Corrected")
    if analytique is not None:
        entetes.append("Formule" if lang == "fr" else "Formula")
    lignes = []
    for i, t in enumerate(tranches):
        cases = [str(i + 1), str(t["n"]),
                 _amplitude(t["amplitude_mediane"], lang, simule),
                 nombre(t["delta"], lang, 2), nombre(t["rho"], lang, 3)]
        if avec_corrigee:
            cases.append(nombre(t["rho_corrigee"], lang, 3))
        if analytique is not None:
            cases.append(nombre(analytique[i], lang, 3))
        lignes.append("<tr>" + "".join(f"<td>{echapper(c)}</td>" for c in cases)
                      + "</tr>")
    th = "".join(f'<th scope="col">{echapper(e)}</th>' for e in entetes)
    return (f'<details class="fig-data">\n<summary>{echapper(resume)}</summary>\n'
            + _scroller(resume)
            + f'<table class="fig-table">\n<thead><tr>{th}</tr></thead>\n'
            f'<tbody>\n' + "\n".join(lignes) + '\n</tbody>\n</table>\n'
            '</div>\n</details>')


# Les memes mots courts d'une figure a l'autre: la serie brute s'appelle
# "brute" partout ou elle apparait, la droite de reference "pleine période".
ETIQ_BRUTE = {"fr": "brute", "en": "raw"}
ETIQ_REF = {"fr": "pleine période", "en": "full sample"}


def fig_constat(ctx, lang):
    titre = ("Corrélation S&P 500 × CAC 40 par décile d'amplitude" if lang == "fr"
             else "S&P 500 × CAC 40 correlation by magnitude decile")
    desc = ("La corrélation d'échantillon monte du premier au dernier décile "
            "d'amplitude du rendement S&P ; la droite horizontale est la "
            "corrélation pleine période." if lang == "fr" else
            "Sample correlation rises from the first to the last decile of "
            "S&P return magnitude; the horizontal line is the full-sample "
            "correlation.")
    etiquettes = {"a": (ETIQ_BRUTE[lang], 4), "reference": (ETIQ_REF[lang], 4)}
    return _tranches_svg(ctx["tranches_reelles"], ctx["rho_pleine"], lang,
                         "fig-constat", titre, desc, etiquettes)


def fig_retournement(ctx, lang):
    titre = ("La même procédure sur un monde à corrélation constante" if lang == "fr"
             else "The same procedure on a constant-correlation world")
    desc = ("Couple gaussien simulé dont la corrélation vraie est constante, "
            "égale à la valeur pleine période du couple réel, soumis à la "
            "même procédure par décile : la courbe monte de la même façon, et "
            "elle suit la prédiction analytique tracée en trait continu." if lang == "fr"
            else
            "Simulated Gaussian pair whose true correlation is constant, equal "
            "to the real pair's full-sample value, put through the same decile "
            "procedure: the curve rises the same way, and it follows the "
            "analytic prediction drawn as a solid line.")
    analytique = [rho_conditionnelle(ctx["rho_pleine"], t["delta"])
                  for t in ctx["tranches_simulees"]]
    # Les points Monte-Carlo et le trait de la formule finissent presque
    # confondus (c'est le message): l'un est nomme au-dessus, l'autre en
    # dessous du point d'arrivee commun.
    etiquettes = {
        "a": ("Monte-Carlo", -8),
        "analytique": ("formule" if lang == "fr" else "formula", 18),
        "reference": (ETIQ_REF[lang], 4),
    }
    return _tranches_svg(ctx["tranches_simulees"], ctx["rho_pleine"], lang,
                         "fig-retournement", titre, desc, etiquettes,
                         courbe_analytique=analytique, simule=True)


def fig_correction(ctx, lang):
    titre = ("Les déciles réels, bruts et corrigés" if lang == "fr"
             else "The real deciles, raw and corrected")
    desc = ("Les mêmes déciles réels, corrélation brute et corrélation corrigée "
            "de Forbes et Rigobon côte à côte. La courbe corrigée reste proche "
            "de la corrélation pleine période là où l'estimateur est serré, du "
            "troisième au dixième décile ; dans les déciles les plus bas "
            "l'inversion amplifie le bruit, et les intervalles larges le disent."
            if lang == "fr" else
            "The same real deciles, raw correlation and Forbes-Rigobon "
            "corrected correlation side by side. The corrected curve stays "
            "near the full-sample correlation where the estimator is tight, "
            "from the third to the tenth decile; in the lowest deciles the "
            "inversion amplifies noise, and the wide intervals say so.")
    etiquettes = {
        "a": (ETIQ_BRUTE[lang], 4),
        "b": ("corrigée" if lang == "fr" else "corrected", 4),
        "reference": (ETIQ_REF[lang], 4),
    }
    return _tranches_svg(ctx["tranches_reelles"], ctx["rho_pleine"], lang,
                         "fig-correction", titre, desc, etiquettes,
                         avec_corrigee=True)


# Les deux crises de la figure 4, bornes en dates de bourse incluses.
EPISODES = [("2008-09-01", "2008-12-31"), ("2020-02-15", "2020-04-30")]
NOMS_EPISODES = {
    "fr": ["automne 2008", "février-avril 2020"],
    "en": ["autumn 2008", "February-April 2020"],
}


def _moyenne_fenetre(dates, valeurs, debut, fin):
    """Moyenne d'une serie glissante sur les fenetres datees dans [debut, fin]."""
    vals = [v for d, v in zip(dates, valeurs) if debut <= d <= fin]
    return sum(vals) / len(vals)


def _tableau_episodes(ctx, lang):
    """La vue tabulaire de la figure 4: une ligne par crise, moyennes des deux
    courbes, plus la reference pleine periode (ou brute et corrigee coincident
    par construction, delta nul)."""
    g = ctx["glissante"]
    resume = "les valeurs des tracés" if lang == "fr" else "the plotted values"
    entetes = (["Épisode", "Brute", "Corrigée"] if lang == "fr"
               else ["Episode", "Raw", "Corrected"])
    lignes = []
    for nom, (debut, fin) in zip(NOMS_EPISODES[lang], EPISODES):
        mb = _moyenne_fenetre(g["dates"], g["brute"], debut, fin)
        mc = _moyenne_fenetre(g["dates"], g["corrigee"], debut, fin)
        lignes.append([nom, nombre(mb, lang, 3), nombre(mc, lang, 3)])
    ref = nombre(ctx["rho_pleine"], lang, 3)
    lignes.append([ETIQ_REF[lang], ref, ref])
    th = "".join(f'<th scope="col">{echapper(e)}</th>' for e in entetes)
    tr = "\n".join("<tr>" + "".join(f"<td>{echapper(c)}</td>" for c in cases)
                   + "</tr>" for cases in lignes)
    return (f'<details class="fig-data">\n<summary>{echapper(resume)}</summary>\n'
            + _scroller(resume)
            + f'<table class="fig-table">\n<thead><tr>{th}</tr></thead>\n'
            f'<tbody>\n{tr}\n</tbody>\n</table>\n'
            '</div>\n</details>')


def fig_reste(ctx, lang):
    """Figure 4: la correlation glissante 60 jours, brute et corrigee, avec les
    deux crises en bandes. Rendu propre, pas le gabarit des deciles: l'axe des
    x est le temps, pas des tranches."""
    g = ctx["glissante"]
    dates, brute, corrigee = g["dates"], g["brute"], g["corrigee"]
    n = len(dates)
    y0, y1 = 32.0, 320.0
    # Les deux courbes restent dans [0, 1] sur toute la periode (minimum reel
    # 0.02 brute, 0.04 corrigee): meme cadre 0..1 que les figures 1 a 3,
    # l'oeil retrouve la grille.
    v0, v1 = 0.0, 1.0

    def x_de(i):
        return round(X0 + i / (n - 1) * (X1 - X0), 2)

    id_fig = "fig-reste"
    titre = ("Corrélation glissante 60 jours, brute et corrigée" if lang == "fr"
             else "60-day rolling correlation, raw and corrected")
    desc = ("Corrélation glissante sur 60 jours entre rendements S&P 500 et "
            "CAC 40, brute et corrigée de Forbes et Rigobon, de 1990 à 2026, "
            "avec l'automne 2008 et février-avril 2020 en bandes. La "
            "correction réduit l'excès des deux crises. La référence de "
            "variance est la pleine période, crises comprises : la correction "
            "sous-corrige, et ce qui resterait au-dessus de la référence en "
            "crise n'est pas à lui seul une preuve de contagion. Chaque "
            "fenêtre porte moins d'information que ses 60 points, d'où des "
            "moyennes par épisode dans le tableau ; dans les fenêtres calmes "
            "la corrigée passe au-dessus de la brute, effet mécanique et "
            "symétrique de l'inversion." if lang == "fr" else
            "60-day rolling correlation between S&P 500 and CAC 40 returns, "
            "raw and Forbes-Rigobon corrected, 1990 to 2026, with autumn 2008 "
            "and February-April 2020 as shaded bands. The correction reduces "
            "the excess of both crises. The variance reference is the full "
            "sample, crises included: the correction under-corrects, and "
            "whatever would stay above the reference in a crisis is not by "
            "itself evidence of contagion. Each window carries less "
            "information than its 60 points, hence per-episode means in the "
            "table; in calm windows the corrected curve runs above the raw "
            "one, a mechanical and symmetric effect of the inversion.")
    parts = [f'<figure class="fig" id="{id_fig}">']
    parts.append(f'<svg class="fig-svg" viewBox="0 0 640 388" role="img" '
                 f'aria-labelledby="{id_fig}-t {id_fig}-d">')
    parts.append(f'<title id="{id_fig}-t">{echapper(titre)}</title>')
    parts.append(f'<desc id="{id_fig}-d">{echapper(desc)}</desc>')
    # Les bandes d'episode d'abord: sous la grille et sous les courbes.
    # Quelques semaines sur 36 ans font une bande de 3 a 5 px: largeur
    # minimale pour qu'elle existe a l'ecran, annee posee au-dessus.
    for debut, fin in EPISODES:
        i0 = bisect.bisect_left(dates, debut)
        i1 = bisect.bisect_right(dates, fin) - 1
        xg = x_de(i0)
        largeur = max(round(x_de(i1) - xg, 2), 3.0)
        parts.append(f'<rect class="fig-episode" x="{xg}" y="{y0}" '
                     f'width="{largeur}" height="{y1 - y0}"/>')
        parts.append(f'<text class="fig-tick" x="{round(xg + largeur / 2, 2)}" '
                     f'y="{y0 - 8}" text-anchor="middle">{debut[:4]}</text>')
    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = sy(v, v0, v1, y0, y1)
        parts.append(f'<line class="fig-grille" x1="{X0}" y1="{y}" x2="{X1}" y2="{y}"/>')
        parts.append(f'<text class="fig-tick fig-tick-y" x="{X0 - 8}" y="{y + 4}">'
                     f'{nombre(v, lang, 2)}</text>')
    yref = sy(ctx["rho_pleine"], v0, v1, y0, y1)
    parts.append(f'<polyline class="fig-repere" points="{X0},{yref} {X1},{yref}"/>')

    # Sous-echantillonnage d'AFFICHAGE, un point sur cinq: ~1800 sommets
    # suffisent aux 474 px de large et divisent le poids de la page par cinq;
    # les tests, eux, courent sur la serie complete.
    def poly(vals):
        idx = list(range(0, n, 5))
        if idx[-1] != n - 1:
            idx.append(n - 1)
        return " ".join(f"{x_de(i)},{sy(vals[i], v0, v1, y0, y1)}" for i in idx)

    parts.append(f'<polyline class="fig-trait fig-trait-fin fig-serie-a" '
                 f'points="{poly(brute)}"/>')
    parts.append(f'<polyline class="fig-trait fig-trait-fin fig-serie-b" '
                 f'points="{poly(corrigee)}"/>')
    # Les noms de serie au contact du dernier point, dans la marge droite;
    # anti-collision si les deux courbes finissent trop proches.
    y_b = sy(brute[-1], v0, v1, y0, y1) + 4
    y_c = sy(corrigee[-1], v0, v1, y0, y1) + 4
    if abs(y_b - y_c) < 14:
        milieu = (y_b + y_c) / 2
        y_b, y_c = ((milieu - 7, milieu + 7) if y_b <= y_c
                    else (milieu + 7, milieu - 7))
    x_et = X1 + 6.0
    parts.append(_etiquette(x_et, y_b, ETIQ_BRUTE[lang]))
    parts.append(_etiquette(x_et, y_c,
                            "corrigée" if lang == "fr" else "corrected"))
    # La reference est nommee sous sa droite, sauf si un nom de courbe y est
    # deja: alors elle passe au-dessus.
    y_ref_et = yref + 14.0
    if min(abs(y_ref_et - y_b), abs(y_ref_et - y_c)) < 14:
        y_ref_et = yref - 6.0
        # et on re-verifie au-dessus: un rafraichissement des donnees peut y
        # amener une courbe, alors on s'ecarte du nom le plus haut (meme
        # regle de 14 px qu'entre les deux noms de courbe).
        if min(abs(y_ref_et - y_b), abs(y_ref_et - y_c)) < 14:
            y_ref_et = min(y_b, y_c) - 14.0
    parts.append(_etiquette(x_et, y_ref_et, ETIQ_REF[lang]))
    # Reperes d'annees: les multiples de 5, a leur premiere date de bourse.
    annees_vues = set()
    for i, d in enumerate(dates):
        an = d[:4]
        if an not in annees_vues:
            annees_vues.add(an)
            if int(an) % 5 == 0:
                parts.append(f'<text class="fig-tick" x="{x_de(i)}" '
                             f'y="{y1 + 18}" text-anchor="middle">{an}</text>')
    parts.append("</svg>")
    parts.append(_tableau_episodes(ctx, lang))
    parts.append("</figure>")
    return "\n".join(parts)


def injecter(chemin, bloc, contenu):
    """Remplace ce qui se trouve entre <!-- fig:bloc --> et <!-- /fig:bloc -->.

    Les reperes doivent EXISTER dans la page: on refuse d'inventer un point
    d'insertion, qui placerait la figure au hasard a la premiere execution.
    """
    texte = chemin.read_text(encoding="utf-8")
    motif = re.compile(rf"(<!-- fig:{bloc} -->).*?(<!-- /fig:{bloc} -->)", re.S)
    if not motif.search(texte):
        raise SystemExit(f"reperes <!-- fig:{bloc} --> absents de {chemin}")
    nouveau = motif.sub(lambda m: m.group(1) + "\n" + contenu + "\n" + m.group(2), texte)
    if nouveau != texte:
        chemin.write_text(nouveau, encoding="utf-8")
    return nouveau != texte
