# tools/contagion/tests/test_build.py
"""L'injection est complete et idempotente, dans les deux pages."""
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
    build.main()
    apres_un = {c: c.read_text(encoding="utf-8") for c in PAGES.values()}
    for texte in apres_un.values():
        for bloc in BLOCS:
            assert "<svg" in texte.split(f"<!-- fig:{bloc} -->")[1] \
                .split(f"<!-- /fig:{bloc} -->")[0]
    build.main()
    for chemin, avant in apres_un.items():
        assert chemin.read_text(encoding="utf-8") == avant, "build non idempotent"
