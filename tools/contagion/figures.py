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
    s = f"{x:.{dec}f}"
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


def _tranches_svg(tranches, rho_reference, lang, id_fig, titre, description,
                  serie_b=None, courbe_analytique=None):
    """Le rendu commun aux figures 1 a 3: deciles en x, correlation en y.

    serie_b: si vrai, trace aussi rho_corrigee et son IC par decile
    (figure 3, la serie corrigee).
    courbe_analytique: liste de valeurs par decile a tracer en trait fin
    (figure 2, la prediction de la formule).
    """
    y0, y1 = 32.0, 320.0
    v0, v1 = 0.0, 1.0
    xs_dec = [sx(i + 0.5, 0, 10) for i in range(10)]
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
        parts.append(f'<line class="fig-ic fig-serie-a" x1="{x}" y1="{ybas}" '
                     f'x2="{x}" y2="{yhaut}"/>')
        parts.append(f'<circle class="fig-point fig-serie-a" cx="{x}" '
                     f'cy="{sy(t["rho"], v0, v1, y0, y1)}" r="4"/>')
    if serie_b is not None:
        for x, t in zip(xs_dec, tranches):
            ybas = sy(t["ic_corr_bas"], v0, v1, y0, y1)
            yhaut = sy(t["ic_corr_haut"], v0, v1, y0, y1)
            parts.append(f'<line class="fig-ic fig-serie-b" x1="{x + 6}" y1="{ybas}" '
                         f'x2="{x + 6}" y2="{yhaut}"/>')
            parts.append(f'<circle class="fig-point fig-serie-b" cx="{x + 6}" '
                         f'cy="{sy(t["rho_corrigee"], v0, v1, y0, y1)}" r="4"/>')
    for i, t in enumerate(tranches):
        parts.append(f'<text class="fig-tick" x="{xs_dec[i]}" y="{y1 + 18}" '
                     f'text-anchor="middle">{i + 1}</text>')
    for i in (0, 4, 9):
        ampl = pourcent(tranches[i]["amplitude_mediane"] * 100, lang, 2)
        parts.append(f'<text class="fig-tick" x="{xs_dec[i]}" y="{y1 + 34}" '
                     f'text-anchor="middle">{echapper(ampl)}</text>')
    axe = ("décile de |rendement S&P|, amplitude médiane en dessous" if lang == "fr"
           else "decile of |S&P return|, median magnitude below")
    parts.append(f'<text class="fig-tick" x="{(X0 + X1) / 2}" y="{y1 + 52}" '
                 f'text-anchor="middle">{echapper(axe)}</text>')
    parts.append("</svg>")
    parts.append(_tableau(tranches, lang, avec_corrigee=serie_b is not None))
    parts.append("</figure>")
    return "\n".join(parts)


def _tableau(tranches, lang, avec_corrigee):
    """Vue tabulaire de la figure, repliee sous <details>: memes classes que
    les tableaux de figures de l'eclipse, sans une ligne de JavaScript."""
    resume = "les valeurs des tracés" if lang == "fr" else "the plotted values"
    entetes = (["Décile", "n", "Amplitude médiane", "δ", "Corrélation"]
               if lang == "fr" else
               ["Decile", "n", "Median magnitude", "δ", "Correlation"])
    if avec_corrigee:
        entetes.append("Corrigée" if lang == "fr" else "Corrected")
    lignes = []
    for i, t in enumerate(tranches):
        cases = [str(i + 1), str(t["n"]),
                 pourcent(t["amplitude_mediane"] * 100, lang, 2),
                 nombre(t["delta"], lang, 2), nombre(t["rho"], lang, 3)]
        if avec_corrigee:
            cases.append(nombre(t["rho_corrigee"], lang, 3))
        lignes.append("<tr>" + "".join(f"<td>{echapper(c)}</td>" for c in cases)
                      + "</tr>")
    th = "".join(f'<th scope="col">{echapper(e)}</th>' for e in entetes)
    return (f'<details class="fig-data">\n<summary>{echapper(resume)}</summary>\n'
            f'<table class="fig-table">\n<thead><tr>{th}</tr></thead>\n'
            f'<tbody>\n' + "\n".join(lignes) + '\n</tbody>\n</table>\n</details>')


def fig_constat(ctx, lang):
    titre = ("Corrélation S&P 500 × CAC 40 par décile d'amplitude" if lang == "fr"
             else "S&P 500 × CAC 40 correlation by magnitude decile")
    desc = ("La corrélation d'échantillon monte du premier au dernier décile "
            "d'amplitude du rendement S&P ; la droite horizontale est la "
            "corrélation pleine période." if lang == "fr" else
            "Sample correlation rises from the first to the last decile of "
            "S&P return magnitude; the horizontal line is the full-sample "
            "correlation.")
    return _tranches_svg(ctx["tranches_reelles"], ctx["rho_pleine"], lang,
                         "fig-constat", titre, desc)


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
