# tools/contagion/build.py
"""Orchestration complete: calcul, injection des figures, export des artefacts.

Usage: source .venv/bin/activate && python3 -m tools.contagion.build

Idempotent par construction: relancer sans changement de code ni de donnees
reecrit exactement les memes octets (graines fixees, injection entre reperes).
"""
from tools.contagion import export, figures


def main():
    ctx = figures.calculer()
    fabriques = {
        "constat": figures.fig_constat,
        "retournement": figures.fig_retournement,
        "correction": figures.fig_correction,
        "reste": figures.fig_reste,
    }
    for lang, chemin in figures.PAGES.items():
        for bloc, fabrique in fabriques.items():
            figures.injecter(chemin, bloc, fabrique(ctx, lang))
        print(chemin.name, "figures injectees")
    export.ecrire()


if __name__ == "__main__":
    main()
