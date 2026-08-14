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
                  etiquettes, serie_b=None, courbe_analytique=None,
                  simule=False):
    """Le rendu commun aux figures 1 a 3: deciles en x, correlation en y.

    etiquettes: dict cle -> (texte, decalage_dy) pour "a", "reference" et,
    selon la figure, "b" ou "analytique"; chaque texte est pose dans la marge
    droite a la hauteur du dernier point du trace qu'il nomme.
    serie_b: si vrai, trace aussi rho_corrigee et son IC par decile
    (figure 3, la serie corrigee).
    courbe_analytique: liste de valeurs par decile a tracer en trait fin
    (figure 2, la prediction de la formule).
    simule: le monde temoin est un couple gaussien SANS unite; son axe ne
    pretend pas etre le rendement S&P et ses amplitudes ne sont pas des
    pourcents (figure 2).
    """
    y0, y1 = 32.0, 320.0
    v0, v1 = 0.0, 1.0
    xs_dec = [sx(i + 0.5, 0, 10) for i in range(10)]
    # Deux series de points: ecart symetrique de 3 px de part et d'autre du
    # centre du decile, pour que les disques de 4 px ne se recouvrent jamais.
    dx_a = -3.0 if serie_b else 0.0
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
    if serie_b is not None:
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
    if serie_b is not None and "b" in etiquettes:
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
    parts.append(_tableau(tranches, lang, avec_corrigee=serie_b is not None,
                          analytique=courbe_analytique, simule=simule))
    parts.append("</figure>")
    return "\n".join(parts)


def _amplitude(v, lang, simule):
    """L'amplitude mediane d'un decile: en pourcent pour les rendements reels,
    en valeur nue pour le monde simule qui n'a pas d'unite."""
    return nombre(v, lang, 2) if simule else pourcent(v * 100, lang, 2)


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
            f'<table class="fig-table">\n<thead><tr>{th}</tr></thead>\n'
            f'<tbody>\n' + "\n".join(lignes) + '\n</tbody>\n</table>\n</details>')


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
    desc = ("Paire gaussienne simulée dont la corrélation vraie est constante, "
            "égale à la valeur pleine période de la paire réelle, soumise à la "
            "même procédure par décile : la courbe monte de la même façon, et "
            "elle suit la prédiction analytique tracée en trait fin." if lang == "fr"
            else
            "Simulated Gaussian pair whose true correlation is constant, equal "
            "to the real pair's full-sample value, put through the same decile "
            "procedure: the curve rises the same way, and it follows the "
            "analytic prediction drawn as a thin line.")
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
                         serie_b=True)


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
