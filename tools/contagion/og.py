"""Les deux images OG (1200x630), rendues depuis le meme calcul que la figure 3.

Usage: source .venv/bin/activate && python3 -m tools.contagion.og

matplotlib ne sert qu'ici: les figures de la page restent du SVG a la main.
Fond et encres repris de la charte sombre du site.

Choix de lecture: la serie corrigee n'est tracee que du 3e au 10e decile,
comme ce que la page defend; le decile 1 corrige (0.88) sort d'une inversion
instable et brouillerait la vignette.
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from tools.contagion.figures import calculer

RACINE = pathlib.Path(__file__).resolve().parents[2]
# charte sombre du site: --paper #191713, --ink #e9e4d8, series des figures
PAPIER, ENCRE = "#191713", "#e9e4d8"
SERIE_A, SERIE_B = "#199e70", "#5b8fe0"   # les couleurs de serie du theme sombre
TITRES = {"fr": ("La contagion, ou moins qu'on ne dit",
                 "brute", "corrigée (déciles 3–10)"),
          "en": ("Contagion, or less than advertised",
                 "raw", "corrected (deciles 3–10)")}


def main():
    ctx = calculer()
    x = list(range(1, 11))
    for lang, (titre, la, lb) in TITRES.items():
        fig, ax = plt.subplots(figsize=(12, 6.3), dpi=100)
        fig.patch.set_facecolor(PAPIER)
        ax.set_facecolor(PAPIER)
        bruts = [t["rho"] for t in ctx["tranches_reelles"]]
        corr = [t["rho_corrigee"] for t in ctx["tranches_reelles"]]
        ax.axhline(ctx["rho_pleine"], color=ENCRE, lw=0.8, alpha=0.4)
        ax.plot(x, bruts, "o-", color=SERIE_A, lw=2, ms=8, label=la)
        # la correction n'est stable que la ou l'amplitude conditionnelle
        # est mesuree proprement: deciles 3 a 10, comme sur la page
        ax.plot(x[2:], corr[2:], "o-", color=SERIE_B, lw=2, ms=8, label=lb)
        ax.set_ylim(0, 1)
        ax.set_xticks(x)
        # la vignette FR parle la meme langue que la page: virgule decimale
        ax.yaxis.set_major_formatter(FuncFormatter(
            lambda v, _, fr=(lang == "fr"):
            f"{v:.1f}".replace(".", ",") if fr else f"{v:.1f}"))
        ax.set_title(titre, color=ENCRE, fontsize=22, pad=18)
        ax.legend(facecolor=PAPIER, labelcolor=ENCRE, edgecolor="none",
                  fontsize=14, loc="upper left")
        ax.tick_params(colors=ENCRE)
        for cote in ax.spines.values():
            cote.set_color(ENCRE)
            cote.set_alpha(0.3)
        fig.text(0.985, 0.03, "nazzareno.fr", color=ENCRE, alpha=0.6,
                 fontsize=12, ha="right", family="monospace")
        # pas de bbox_inches="tight": il changerait la taille en pixels,
        # et la spec OG veut exactement 1200x630
        fig.subplots_adjust(left=0.06, right=0.97, top=0.86, bottom=0.12)
        nom = "contagion.jpg" if lang == "fr" else "contagion-en.jpg"
        fig.savefig(RACINE / "assets" / "og" / nom, format="jpg",
                    facecolor=PAPIER)
        plt.close(fig)
        print(nom)


if __name__ == "__main__":
    main()
