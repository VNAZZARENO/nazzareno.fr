"""Trois figures SVG de la page eclipse, calculees puis injectees dans le HTML.

Usage: source .venv/bin/activate && python3 -m tools.eclipse.figures

A lancer depuis la RACINE du depot.

Pourquoi du SVG ecrit a la main plutot qu'une bibliotheque de trace: la page
promet de fonctionner sans une ligne de JavaScript et sans dependance, et ces
trois figures doivent tenir cette promesse comme le reste. Du SVG en ligne
herite en plus des variables CSS de la page, donc du schema clair ET du schema
sombre, ce qu'une image rasterisee ne saurait pas faire.

Les trois courbes sortent du MEME modele que le reste de la page
(tools.eclipse.geometry et tools.eclipse.limb, loi de Pierce & Slaughter 1977),
et les points repere sortent du MEME fichier que le tableau des contacts. Aucun
nombre n'est saisi a la main ici: s'ils divergeaient un jour, ce serait le
signe d'un bug, pas d'un oubli de mise a jour.

Deux decisions de trace meritent d'etre ecrites.

1. LA FIGURE 1 A DEUX PANNEAUX, et ce n'est pas de la decoration. Sur un axe de
   0 a 100 %, la courbe reelle et la droite du disque uniforme sont separees
   d'au plus 3,6 POINTS: a cette echelle les deux traces se confondent et la
   figure ne montrerait rien du tout. Le panneau du bas trace donc leur ecart,
   ou le meme fait devient lisible et ou le croisement est un passage par zero.
   Deux panneaux qui PARTAGENT l'abscisse, jamais deux echelles verticales sur
   un meme trace.

2. LES COULEURS DE SERIE NE SONT PAS L'ACCENT VERT DU SITE. Mesure au
   validateur de palette, il tombe sous le plancher de chroma et se lit comme
   du gris des qu'il porte une courbe. Le couple retenu passe les cinq
   controles (bande de clarte, chroma, separation daltonienne, plancher en
   vision normale, contraste) sur les DEUX fonds de la page. Le texte, lui,
   reste toujours a l'encre: c'est la courbe posee a cote de l'etiquette qui
   porte l'identite, jamais la couleur du mot.
"""

import json
import math
import pathlib
import re

from tools.eclipse import geometry, limb

RACINE = pathlib.Path(__file__).resolve().parents[2]
DONNEES = RACINE / "assets" / "data" / "eclipse-2026-08-12.json"
PAGES = {
    "fr": RACINE / "projets" / "eclipse.html",
    "en": RACINE / "en" / "projects" / "eclipse.html",
}

# Luminance relative sRGB. Meme ponderation que le shader du ciel (LUMA).
LUMA = (0.2126, 0.7152, 0.0722)

# Subdivisions radiales de l'integrale de flux. build.py en utilise 512 pour le
# fichier de donnees; on garde la meme valeur pour que les courbes passent
# exactement par les points du tableau et non a cote.
ANNEAUX = 512

# Echantillons le long de la separation des deux disques. On balaie d et non
# l'obscuration: l'obscuration s'en deduit exactement, alors que l'inverse
# demanderait une inversion numerique a chaque point.
N_POINTS = 480

# Cadre commun. L'abscisse est TOUJOURS l'obscuration, de 0 a 1.
L = 640
MG, MD = 54, 112          # marges gauche (graduations) et droite (etiquettes)
X0, X1 = MG, L - MD


def fmt(v):
    """Formate un nombre pour le SVG, sans zeros inutiles."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def px(o):
    return X0 + o * (X1 - X0)


def echapper(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nombre(v, lang, decimales=2):
    s = f"{v:.{decimales}f}"
    return s.replace(".", ",") if lang == "fr" else s


def pourcent(v, lang, decimales=2):
    """Espace insecable avant % en francais, rien en anglais."""
    return (f"{nombre(v, lang, decimales)} %" if lang == "fr"
            else f"{nombre(v, lang, decimales)}%")


def points_pct(v, lang, decimales=2):
    """Une DIFFERENCE de pourcentages s'exprime en points, jamais en pour cent."""
    signe = "+" if v >= 0 else "−"
    return f"{signe}{nombre(abs(v), lang, decimales)} pt"


# -- le modele -----------------------------------------------------------------

def lstar(Y):
    """Clarte perceptuelle L* de la CIE (1976), ramenee a [0, 1].

    Ce n'est PAS une mesure de ce qu'un temoin a vu: L* decrit la clarte percue
    d'une surface a adaptation FIXE, alors qu'un oeil sous une eclipse s'adapte
    en plus. La courbe SOUS-ESTIME donc l'effet qu'elle illustre, ce que dit la
    legende de la figure.
    """
    seuil = (6 / 29) ** 3
    f = Y ** (1 / 3) if Y > seuil else (841 / 108) * Y + 4 / 29
    return (116 * f - 16) / 100


def serie(r_sun, r_moon):
    """(obscuration, flux luminance, flux rouge, flux bleu) le long de d."""
    points = []
    for i in range(N_POINTS + 1):
        d = (r_sun + r_moon) * (1.0 - i / N_POINTS)
        o = geometry.obscuration(d, r_sun, r_moon)
        f_r, f_v, f_b = limb.rgb_flux_fraction(d, r_sun, r_moon, n=ANNEAUX)
        y = LUMA[0] * f_r + LUMA[1] * f_v + LUMA[2] * f_b
        points.append((o, y, f_r, f_b))
    return points


def croisement(points):
    """Obscuration ou le flux reel passe sous la droite du disque uniforme."""
    precedent = None
    for o, y, *_ in points:
        ecart = y - (1.0 - o)
        if precedent is not None and precedent[1] > 0.0 >= ecart:
            o0, e0 = precedent
            return o0 + (o - o0) * e0 / (e0 - ecart)
        precedent = (o, ecart)
    raise SystemExit("aucun croisement trouve: le modele a change")


def au_plus_pres(points, cible):
    return min(points, key=lambda p: abs(p[0] - cible))


# -- panneau -------------------------------------------------------------------

class Panneau:
    """Une zone de trace. Plusieurs panneaux peuvent partager l'abscisse; il n'y
    a jamais deux echelles verticales sur un meme trace."""

    def __init__(self, y0, y1, ymin, ymax, graduations, format_y, titre=None):
        self.y0, self.y1 = y0, y1
        self.ymin, self.ymax = ymin, ymax
        self.graduations = graduations
        self.format_y = format_y
        self.titre = titre

    def y(self, v):
        return self.y1 - (v - self.ymin) / (self.ymax - self.ymin) * (self.y1 - self.y0)

    def grille(self):
        out = []
        if self.titre:
            out.append(f'<text class="fig-titre" x="{X0}" y="{fmt(self.y0 - 12)}">'
                       f'{echapper(self.titre)}</text>')
        for v in self.graduations:
            y = self.y(v)
            out.append(f'<line class="fig-grille" x1="{X0}" y1="{fmt(y)}" '
                       f'x2="{X1}" y2="{fmt(y)}"/>')
            out.append(f'<text class="fig-tick fig-tick-y" x="{X0 - 8}" '
                       f'y="{fmt(y + 4)}">{echapper(self.format_y(v))}</text>')
        return "\n".join(out)

    def ligne_zero(self, v=0.0):
        y = self.y(v)
        return f'<line class="fig-axe" x1="{X0}" y1="{fmt(y)}" x2="{X1}" y2="{fmt(y)}"/>'

    def courbe(self, points, classe):
        coords = " ".join(f"{fmt(px(o))},{fmt(self.y(v))}" for o, v in points)
        return f'<polyline class="{classe}" points="{coords}"/>'

    def point(self, o, v, texte, dx=10, dy=-10, ancre="start"):
        """Marque repere: anneau dans la couleur du fond plutot qu'un contour,
        pour qu'elle se detache meme posee sur une courbe."""
        x, y = px(o), self.y(v)
        return (f'<circle class="fig-point" cx="{fmt(x)}" cy="{fmt(y)}" r="4"/>\n'
                f'<text class="fig-note" text-anchor="{ancre}" x="{fmt(x + dx)}" '
                f'y="{fmt(y + dy)}">{echapper(texte)}</text>')

    def etiquette(self, o, v, texte, dx=8, dy=4, ancre="start"):
        """Nom de serie pose AU CONTACT de sa courbe: l'identite ne repose jamais
        sur la seule couleur, et le mot reste a l'encre."""
        x, y = px(o), self.y(v)
        return (f'<text class="fig-serie" text-anchor="{ancre}" x="{fmt(x + dx)}" '
                f'y="{fmt(y + dy)}">{echapper(texte)}</text>')


def axe_x(y, lang, titre):
    out = []
    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<text class="fig-tick fig-tick-x" x="{fmt(px(v))}" y="{y}">'
                   f'{echapper(pourcent(v * 100, lang, 0))}</text>')
    out.append(f'<text class="fig-titre fig-tick-x" x="{fmt(px(0.5))}" y="{y + 24}">'
               f'{echapper(titre)}</text>')
    return "\n".join(out)


def svg(corps, hauteur, titre, description, ident):
    return (f'<svg class="fig-svg" viewBox="0 0 {L} {hauteur}" role="img" '
            f'aria-labelledby="{ident}-t {ident}-d">\n'
            f'<title id="{ident}-t">{echapper(titre)}</title>\n'
            f'<desc id="{ident}-d">{echapper(description)}</desc>\n'
            f'{corps}\n</svg>')


def tableau(entetes, lignes, resume):
    """Vue tabulaire de la figure, repliee. Toute figure doit exister aussi sous
    forme de nombres; <details> le fait sans une ligne de JavaScript."""
    th = "".join(f'<th scope="col">{echapper(h)}</th>' for h in entetes)
    tr = "\n".join("<tr>" + "".join(f"<td>{echapper(c)}</td>" for c in ligne) + "</tr>"
                   for ligne in lignes)
    return (f'<details class="fig-data">\n<summary>{echapper(resume)}</summary>\n'
            f'<table class="fig-table">\n<thead><tr>{th}</tr></thead>\n'
            f'<tbody>\n{tr}\n</tbody>\n</table>\n</details>')


def figure(ident, contenu_svg, legende, table):
    return (f'<figure class="fig" id="{ident}">\n{contenu_svg}\n'
            f'<figcaption>{legende}</figcaption>\n{table}\n</figure>')


def pct0(lang):
    return lambda v: pourcent(v * 100, lang, 0)


# -- figure 1: flux residuel contre obscuration --------------------------------

TEXTES_1 = {
    "fr": {
        "titre": "Flux résiduel en fonction de l'obscuration",
        "desc": ("Deux panneaux partageant l'axe de l'obscuration. En haut, le flux "
                 "restant et la droite du disque uniformément brillant, presque "
                 "confondus. En bas, leur écart en points : positif jusqu'à 33 % "
                 "d'obscuration, négatif ensuite, avec un creux de 3,6 points vers 78 %."),
        "panneau_a": "a. le flux qui reste : les deux tracés se confondent presque",
        "panneau_b": "b. leur écart, en points de pourcentage",
        "axe_x": "obscuration",
        "reel": "flux réel",
        "naif": "disque uniforme",
        "plus": "il reste plus de lumière que la surface ne le dit",
        "moins": "il en reste moins",
        "croisement": "croisement, {o}",
        "paris": "maximum parisien, {v}",
        "resume": "les valeurs des deux tracés",
        "entetes": ["Obscuration", "Flux réel", "Disque uniforme", "Écart"],
        "legende": ("Le flux qui reste quand la Lune couvre une fraction croissante du "
                    "Soleil. La droite grise est ce que donnerait un disque uniformément "
                    "brillant, <em>1 − obscuration</em> ; la courbe est le calcul réel, "
                    "assombrissement centre-bord compris. Sur un axe de 0 à 100 % les deux "
                    "se confondent, d'où le second panneau : l'écart y passe par zéro à "
                    "{o} d'obscuration, culmine à {haut} vers {o_haut}, et creuse à {bas} "
                    "vers {o_bas}. La courbe ne dépend qu'imperceptiblement du rapport des "
                    "rayons apparents, moins de 0,01 point entre les trois lieux ; "
                    "celle-ci est tracée avec ceux de Paris."),
    },
    "en": {
        "titre": "Residual flux against obscuration",
        "desc": ("Two panels sharing the obscuration axis. Above, the remaining flux and "
                 "the uniformly bright disc line, almost on top of each other. Below, "
                 "the difference in points: positive up to 33% obscuration, negative "
                 "after, with a trough of 3.6 points around 78%."),
        "panneau_a": "a. the flux that is left: the two traces almost coincide",
        "panneau_b": "b. their difference, in percentage points",
        "axe_x": "obscuration",
        "reel": "real flux",
        "naif": "uniform disc",
        "plus": "more light remains than the area says",
        "moins": "less remains",
        "croisement": "crossover, {o}",
        "paris": "Paris maximum, {v}",
        "resume": "the values behind both traces",
        "entetes": ["Obscuration", "Real flux", "Uniform disc", "Difference"],
        "legende": ("The flux left as the Moon covers a growing fraction of the Sun. The "
                    "grey line is what a uniformly bright disc would give, "
                    "<em>1 − obscuration</em>; the curve is the real computation, limb "
                    "darkening included. On a 0-to-100% axis the two coincide, hence the "
                    "second panel: the difference crosses zero at {o} obscuration, peaks "
                    "at {haut} around {o_haut}, and troughs at {bas} around {o_bas}. The "
                    "curve depends only imperceptibly on the ratio of the apparent radii, "
                    "less than 0.01 point across the three places; this one is drawn with "
                    "the Paris values."),
    },
}


def figure_flux(points, lang, repere_paris):
    t = TEXTES_1[lang]
    o_c = croisement(points)
    o_paris, f_paris = repere_paris
    ecarts = [(o, (y - (1.0 - o)) * 100.0) for o, y, *_ in points]
    haut = max(ecarts, key=lambda p: p[1])
    bas = min(ecarts, key=lambda p: p[1])

    a = Panneau(32, 232, 0.0, 1.0, (0.0, 0.25, 0.5, 0.75, 1.0), pct0(lang),
                t["panneau_a"])
    b = Panneau(306, 416, -4.3, 2.7, (-4.0, -2.0, 0.0, 2.0),
                lambda v: points_pct(v, lang, 0), t["panneau_b"])

    corps = [a.grille(), a.ligne_zero(0.0)]
    corps.append(a.courbe([(0.0, 1.0), (1.0, 0.0)], "fig-repere"))
    corps.append(a.courbe([(o, y) for o, y, *_ in points], "fig-trait fig-a"))
    corps.append(a.etiquette(1.0, 0.055, t["reel"], dx=8, dy=0))
    corps.append(a.etiquette(1.0, 0.0, t["naif"], dx=8, dy=4))
    # Pas de repere parisien dans ce panneau: la droite grise y est diagonale,
    # aucune etiquette horizontale ne l'evite, et le message du panneau est que
    # les deux traces se confondent. Le chiffre est dans la legende, dans le
    # tableau et sur la figure de l'oeil.

    corps.append(b.grille())
    corps.append(b.ligne_zero(0.0))
    corps.append(b.courbe(ecarts, "fig-trait fig-a"))
    corps.append(b.etiquette(0.02, 2.35, t["plus"], dx=0, dy=0))
    corps.append(b.etiquette(1.0, -3.6, t["moins"], dx=8, dy=4))
    corps.append(b.point(o_c, 0.0, t["croisement"].format(o=pourcent(o_c * 100, lang, 1)),
                         dx=10, dy=-10))
    corps.append(b.point(bas[0], bas[1], points_pct(bas[1], lang, 1),
                         dx=0, dy=20, ancre="middle"))

    corps.append(axe_x(444, lang, t["axe_x"]))

    lignes = []
    for k in range(11):
        p = au_plus_pres(points, k / 10)
        naif = 1.0 - p[0]
        lignes.append([
            pourcent(p[0] * 100, lang, 1),
            pourcent(p[1] * 100, lang, 2),
            pourcent(naif * 100, lang, 2),
            points_pct((p[1] - naif) * 100, lang, 2),
        ])

    return figure(
        "fig-flux",
        svg("\n".join(corps), 484, t["titre"], t["desc"], "fig-flux"),
        t["legende"].format(o=pourcent(o_c * 100, lang, 1),
                            haut=points_pct(haut[1], lang, 1),
                            o_haut=pourcent(haut[0] * 100, lang, 0),
                            bas=points_pct(bas[1], lang, 1),
                            o_bas=pourcent(bas[0] * 100, lang, 0)),
        tableau(t["entetes"], lignes, t["resume"]),
    )


# -- figure 2: rapport du flux rouge au flux bleu ------------------------------
# Une seule serie: le titre la nomme, aucune legende de couleurs n'est utile.

TEXTES_2 = {
    "fr": {
        "titre": "Rapport du flux rouge au flux bleu",
        "desc": ("Rapport entre le flux rouge et le flux bleu restants, en fonction de "
                 "l'obscuration. Il vaut 1 sans éclipse, descend imperceptiblement sous "
                 "1 au début, puis monte franchement en partielle profonde : la lumière "
                 "qui reste devient plus chaude."),
        "neutre": "lumière inchangée",
        "paris": "maximum parisien, {v}",
        "axe_x": "obscuration",
        "resume": "les valeurs de la courbe",
        "entetes": ["Obscuration", "Flux rouge", "Flux bleu", "Rouge / bleu"],
        "legende": ("L'assombrissement centre-bord est plus marqué dans le bleu que dans "
                    "le rouge : la couleur du flux restant change donc au cours de "
                    "l'éclipse. Au tout début la Lune mord un limbe relativement rouge et "
                    "le rapport passe très légèrement sous 1, jusqu'à {creux} vers "
                    "{o_creux} ; en partielle profonde il monte franchement et atteint "
                    "{paris} au maximum parisien. Le tracé s'arrête à {fin} d'obscuration : "
                    "au-delà il ne reste qu'un filet de limbe, le rapport s'envole et "
                    "écraserait tout le reste de la courbe."),
    },
    "en": {
        "titre": "Ratio of red flux to blue flux",
        "desc": ("Ratio of the remaining red flux to the remaining blue flux against "
                 "obscuration. It is 1 outside the eclipse, dips imperceptibly below 1 "
                 "early on, then rises clearly deep into the partial phase: the light "
                 "that is left grows warmer."),
        "neutre": "light unchanged",
        "paris": "Paris maximum, {v}",
        "axe_x": "obscuration",
        "resume": "the values behind the curve",
        "entetes": ["Obscuration", "Red flux", "Blue flux", "Red / blue"],
        "legende": ("Limb darkening is stronger in the blue than in the red, so the colour "
                    "of the remaining flux shifts as the eclipse goes on. Right at the "
                    "start the Moon bites into a relatively red limb and the ratio slips "
                    "just below 1, down to {creux} around {o_creux}; deep into the partial "
                    "it climbs clearly and reaches {paris} at the Paris maximum. The trace "
                    "stops at {fin} obscuration: past that only a thread of limb is left, "
                    "the ratio runs away and would flatten the rest of the curve."),
    },
}

FIN_COULEUR = 0.99


def figure_couleur(points, lang, repere_paris_rb):
    t = TEXTES_2[lang]
    o_paris, rb_paris = repere_paris_rb
    utiles = [(o, r / b) for o, _, r, b in points if b > 0.0 and o <= FIN_COULEUR]
    creux = min(utiles, key=lambda p: p[1])

    p = Panneau(32, 320, 0.95, 1.33, (1.0, 1.1, 1.2, 1.3),
                lambda v: nombre(v, lang, 2))

    corps = [p.grille()]
    corps.append(p.courbe([(0.0, 1.0), (1.0, 1.0)], "fig-repere"))
    corps.append(p.courbe(utiles, "fig-trait fig-a"))
    corps.append(p.etiquette(0.08, 1.0, t["neutre"], dx=0, dy=-10))
    corps.append(p.point(o_paris, rb_paris,
                         t["paris"].format(v=nombre(rb_paris, lang, 3)),
                         dx=-12, dy=-10, ancre="end"))
    corps.append(axe_x(348, lang, t["axe_x"]))

    lignes = []
    for k in range(11):
        o, y, r, b = au_plus_pres(points, k / 10)
        lignes.append([
            pourcent(o * 100, lang, 1),
            pourcent(r * 100, lang, 3),
            pourcent(b * 100, lang, 3),
            nombre(r / b, lang, 4) if b > 0 else ("n. d." if lang == "fr" else "n/a"),
        ])

    return figure(
        "fig-couleur",
        svg("\n".join(corps), 388, t["titre"], t["desc"], "fig-couleur"),
        t["legende"].format(creux=nombre(creux[1], lang, 4),
                            o_creux=pourcent(creux[0] * 100, lang, 0),
                            paris=nombre(rb_paris, lang, 3),
                            fin=pourcent(FIN_COULEUR * 100, lang, 0)),
        tableau(t["entetes"], lignes, t["resume"]),
    )


# -- figure 3: flux reel contre clarte percue ----------------------------------

TEXTES_3 = {
    "fr": {
        "titre": "Flux réel et clarté perçue",
        "desc": ("Deux courbes en fonction de l'obscuration : le flux lumineux réellement "
                 "restant, et la clarté perçue correspondante selon la grandeur L* de la "
                 "CIE. Au maximum parisien il reste 5,45 % du flux mais encore 28 % de "
                 "clarté perçue."),
        "reel": "flux réel",
        "percu": "clarté perçue (modèle)",
        "paris_reel": "{v} du flux",
        "paris_percu": "{v} de clarté",
        "axe_x": "obscuration",
        "resume": "les valeurs des deux courbes",
        "entetes": ["Obscuration", "Flux réel", "Clarté perçue L*", "Crans de diaphragme"],
        "legende": ("La physique retire la lumière bien plus vite que l'œil n'en rend "
                    "compte. Au maximum parisien il ne reste que {flux} du flux, soit "
                    "{crans} crans de diaphragme, et pourtant la clarté perçue tient "
                    "encore à {percu}. L'écart entre les deux courbes est toute la réponse "
                    "à la question de départ. <strong>La courbe grise est un modèle, pas "
                    "une mesure</strong> : c'est la clarté L* de la CIE (1976), définie à "
                    "adaptation fixe, alors qu'un œil sous une éclipse s'adapte en plus. "
                    "Elle sous-estime donc l'effet qu'elle illustre."),
    },
    "en": {
        "titre": "Real flux and perceived lightness",
        "desc": ("Two curves against obscuration: the light flux actually remaining, and "
                 "the matching perceived lightness under the CIE L* measure. At the Paris "
                 "maximum 5.45% of the flux is left but still 28% of the perceived "
                 "lightness."),
        "reel": "real flux",
        "percu": "perceived lightness (model)",
        "paris_reel": "{v} of the flux",
        "paris_percu": "{v} lightness",
        "axe_x": "obscuration",
        "resume": "the values behind both curves",
        "entetes": ["Obscuration", "Real flux", "Perceived lightness L*", "Stops"],
        "legende": ("Physics takes light away far faster than the eye reports it. At the "
                    "Paris maximum only {flux} of the flux is left, which is {crans} "
                    "stops, and yet the perceived lightness still holds at {percu}. The gap "
                    "between the two curves is the whole answer to the opening question. "
                    "<strong>The grey curve is a model, not a measurement</strong>: it is "
                    "CIE L* lightness (1976), defined at fixed adaptation, whereas an eye "
                    "under an eclipse adapts as well. It therefore understates the very "
                    "effect it illustrates."),
    },
}


def figure_oeil(points, lang, repere_paris):
    t = TEXTES_3[lang]
    o_paris, f_paris = repere_paris
    l_paris = lstar(f_paris)

    p = Panneau(32, 320, 0.0, 1.0, (0.0, 0.25, 0.5, 0.75, 1.0), pct0(lang))

    corps = [p.grille(), p.ligne_zero(0.0)]
    corps.append(p.courbe([(o, lstar(y)) for o, y, *_ in points],
                          "fig-trait fig-repere"))
    corps.append(p.courbe([(o, y) for o, y, *_ in points], "fig-trait fig-a"))

    ref = au_plus_pres(points, 0.52)
    corps.append(p.etiquette(0.52, ref[1], t["reel"], dx=6, dy=19))
    corps.append(p.etiquette(0.52, lstar(ref[1]), t["percu"], dx=6, dy=-11))
    corps.append(p.point(o_paris, l_paris,
                         t["paris_percu"].format(v=pourcent(l_paris * 100, lang, 1)),
                         # a la hauteur du point et non au-dessus: la courbe grise
                         # monte a gauche, donc une etiquette posee a plat sous
                         # elle ne peut plus la croiser.
                         dx=-14, dy=4, ancre="end"))
    corps.append(p.point(o_paris, f_paris,
                         t["paris_reel"].format(v=pourcent(f_paris * 100, lang, 2)),
                         dx=-12, dy=17, ancre="end"))
    corps.append(axe_x(348, lang, t["axe_x"]))

    lignes = []
    for k in range(11):
        o, y, *_ = au_plus_pres(points, k / 10)
        # a obscuration totale il ne reste rien: le logarithme diverge, et
        # "moins l'infini" est plus juste qu'un tiret muet.
        crans = "\u2212\u221e" if y <= 0 else nombre(math.log2(y), lang, 2)
        lignes.append([
            pourcent(o * 100, lang, 1),
            pourcent(y * 100, lang, 2),
            pourcent(lstar(y) * 100, lang, 1),
            crans,
        ])

    return figure(
        "fig-oeil",
        svg("\n".join(corps), 388, t["titre"], t["desc"], "fig-oeil"),
        t["legende"].format(flux=pourcent(f_paris * 100, lang, 2),
                            percu=pourcent(l_paris * 100, lang, 1),
                            crans=nombre(abs(math.log2(f_paris)), lang, 1)),
        tableau(t["entetes"], lignes, t["resume"]),
    )


# -- les trois disques au maximum ----------------------------------------------
# Les images sont produites par la route ?disque=<id> de main.js, donc par le
# shader de l'encart lui-meme. Ce bloc-ci n'ecrit que le balisage et les
# legendes, et il tire ses nombres du meme fichier que le tableau des contacts.

TEXTES_D = {
    "fr": {
        "resume": "Les trois disques au maximum, calculés pour chaque lieu.",
        "locales": "{h} locales",
        "chiffres": "{obsc} d'obscuration, Soleil à {alt}",
        "note": ("Vue téléobjectif, champ de {champ}, même échelle pour les trois : le "
                 "Soleil occupe un tiers du cadre. Ces images sortent du shader de "
                 "l'encart du simulateur, à la seule différence de la taille du "
                 "rendu, et donc des mêmes éphémérides que le tableau ci-dessus. "
                 "<strong>Elles n'appliquent aucune extinction atmosphérique</strong> : "
                 "à Palma, à 2,64° de hauteur et sous une vingtaine de masses d'air, "
                 "le vrai disque était rouge sombre et la vraie couronne bien plus faible. "
                 "La couronne suit la loi radiale de van de Hulst et Baumbach, hérissée de "
                 "jets procéduraux : elle est plausible pour un maximum d'activité, "
                 "ce n'est pas la couronne observée du 12 août."),
        "alt": {
            "paris": ("Le Soleil de Paris au maximum : un croissant fin et net, ouvert "
                      "vers le bas, sur un champ noir. Le croissant est légèrement plus "
                      "chaud vers ses pointes, où l'on voit le limbe."),
            "espagne": ("Le Soleil de Palma de Majorque pendant la totalité : le disque "
                        "noir de la Lune, entouré d'un anneau de couronne solaire "
                        "brillante qui s'étend en jets sur tout le cadre."),
            "reykjavik": ("Le Soleil de Reykjavík pendant la totalité : le disque noir de "
                          "la Lune, un peu plus large qu'à Palma, entouré de la "
                          "couronne solaire."),
        },
    },
    "en": {
        "resume": "The three discs at maximum, computed for each place.",
        "locales": "{h} local time",
        "chiffres": "{obsc} obscuration, Sun at {alt}",
        "note": ("Telephoto view, {champ} field, same scale for all three: the Sun fills a "
                 "third of the frame. These images come out of the simulator's own "
                 "inset shader, differing only in render size, and therefore from the same "
                 "ephemerides as the table above. <strong>They apply no atmospheric "
                 "extinction</strong>: in Palma, 2.64° up and under some twenty air masses, "
                 "the real disc was deep red and the real corona far fainter. The corona "
                 "follows the van de Hulst and Baumbach radial law with procedural "
                 "streamers: it is plausible for a solar maximum, it is not the observed "
                 "corona of 12 August."),
        "alt": {
            "paris": ("The Sun from Paris at maximum: a thin, sharp crescent opening "
                      "downwards on a black field. The crescent is slightly warmer towards "
                      "its horns, where the limb shows."),
            "espagne": ("The Sun from Palma de Mallorca during totality: the black disc of "
                        "the Moon ringed by a bright solar corona reaching out in streamers "
                        "across the frame."),
            "reykjavik": ("The Sun from Reykjavík during totality: the black disc of the "
                          "Moon, a little wider than at Palma, ringed by the solar corona."),
        },
    },
}

# Champ de l'encart, en degres. MEME valeur que CHAMP_DEG dans
# assets/js/eclipse/inset.glsl.js: si l'une bougeait sans l'autre, la legende
# annoncerait un cadrage que les images n'ont pas.
CHAMP_DEG = 1.5


def heure_locale(site, lang):
    import datetime
    import zoneinfo
    t0 = datetime.datetime.fromisoformat(site["t0_utc"].replace("Z", "+00:00"))
    tmax = (t0 + datetime.timedelta(seconds=site["t_max_s"])).astimezone(
        zoneinfo.ZoneInfo(site["tz"]))
    if lang == "fr":
        return f"{tmax:%H} h {tmax:%M} min {tmax:%S} s"
    return f"{tmax:%H:%M:%S}"


def figure_disques(donnees, lang):
    t = TEXTES_D[lang]
    cartes = []
    for site in donnees["sites"]:
        image = site["frames"][round(site["t_max_s"] / site["step_s"])]
        obsc, alt = image[7], image[1]
        nom = site["name_fr"] if lang == "fr" else site["name_en"]
        chiffres = t["chiffres"].format(
            obsc=pourcent(obsc * 100, lang, 2),
            alt=f'{nombre(alt, lang, 2)}\u00b0')
        cartes.append(
            f'<figure class="disque">\n'
            f'<a href="/assets/img/eclipse-disque-{site["id"]}.webp">'
            f'<img src="/assets/img/eclipse-disque-{site["id"]}.webp" '
            f'width="1200" height="1200" loading="lazy" decoding="async" '
            f'alt="{echapper(t["alt"][site["id"]])}"></a>\n'
            f'<figcaption><b>{echapper(nom)}</b>'
            f'<span>{echapper(t["locales"].format(h=heure_locale(site, lang)))}</span>'
            f'<span>{echapper(chiffres)}</span></figcaption>\n</figure>')

    champ = f'{nombre(CHAMP_DEG, lang, 1)}\u00b0'
    return (f'<div class="disques" role="group" aria-label="{echapper(t["resume"])}">\n'
            + "\n".join(cartes)
            + f'\n</div>\n<p class="disques-note">{t["note"].format(champ=champ)}</p>')


# -- injection -----------------------------------------------------------------

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


def main():
    donnees = json.loads(DONNEES.read_text(encoding="utf-8"))
    paris = next(s for s in donnees["sites"] if s["id"] == "paris")
    image = paris["frames"][round(paris["t_max_s"] / paris["step_s"])]
    r_sun, r_moon = image[4], image[5]
    # Les points repere sortent du FICHIER, pas d'un nouveau calcul: ce sont les
    # memes nombres que ceux du tableau des contacts, a l'octet pres.
    o_paris = image[7]
    f_paris = LUMA[0] * image[8] + LUMA[1] * image[9] + LUMA[2] * image[10]
    rb_paris = image[8] / image[10]

    points = serie(r_sun, r_moon)
    print(f"serie: {len(points)} points, rSun={r_sun:.6f} rMoon={r_moon:.6f}")
    print(f"croisement a {croisement(points) * 100:.3f} % d'obscuration")
    print(f"Paris: obsc {o_paris * 100:.2f} %, flux {f_paris * 100:.3f} %, "
          f"L* {lstar(f_paris) * 100:.2f} %, R/B {rb_paris:.4f}")

    for lang, chemin in PAGES.items():
        blocs = {
            "flux": figure_flux(points, lang, (o_paris, f_paris)),
            "couleur": figure_couleur(points, lang, (o_paris, rb_paris)),
            "oeil": figure_oeil(points, lang, (o_paris, f_paris)),
            "disques": figure_disques(donnees, lang),
        }
        for nom, contenu in blocs.items():
            change = injecter(chemin, nom, contenu)
            print(f"  {lang} fig:{nom} {'mis a jour' if change else 'inchange'}")


if __name__ == "__main__":
    main()
