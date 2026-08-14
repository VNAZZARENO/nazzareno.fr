# tools/contagion/tests/test_figures.py
"""Ce que les legendes affirment, un test par affirmation."""
import re

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
