# tools/contagion/tests/test_build.py
"""L'injection est complete et idempotente, dans les deux pages.

Le premier passage de build.main() sert aussi de garde de peremption: il doit
laisser TOUS les octets geres (pages ET artefacts d'export) identiques a l'etat
commite, sinon quelqu'un a change le code ou les donnees sans relancer le build.
Snapshot AVANT le premier build: sans cela, build.main() rafraichirait les
artefacts avant que test_export ne fige son propre "avant", et un fichier
corrompu passerait la suite.
"""
from tools.contagion.figures import PAGES

BLOCS = ["constat", "retournement", "correction", "reste"]


def test_reperes_presents_dans_les_deux_pages():
    for chemin in PAGES.values():
        texte = chemin.read_text(encoding="utf-8")
        for bloc in BLOCS:
            assert f"<!-- fig:{bloc} -->" in texte, (chemin.name, bloc)
            assert f"<!-- /fig:{bloc} -->" in texte, (chemin.name, bloc)


def test_figures_injectees_et_idempotence():
    from tools.contagion import build
    from tools.contagion.figures import RACINE
    geres = list(PAGES.values()) + [
        RACINE / "assets" / "data" / "contagion.json",
        RACINE / "tools" / "js-tests" / "fixture-contagion.json",
    ]
    avant_build = {c: c.read_bytes() for c in geres}
    build.main()
    for chemin in geres:
        assert chemin.read_bytes() == avant_build[chemin], \
            f"{chemin.name}: etat commite perime, relancer python3 -m tools.contagion.build et commiter"
    # idempotence stricte: une seconde passe ne change plus un octet
    build.main()
    for chemin in geres:
        assert chemin.read_bytes() == avant_build[chemin], "build non idempotent"
    for chemin in PAGES.values():
        texte = chemin.read_text(encoding="utf-8")
        for bloc in BLOCS:
            assert "<svg" in texte.split(f"<!-- fig:{bloc} -->")[1].split(f"<!-- /fig:{bloc} -->")[0]
