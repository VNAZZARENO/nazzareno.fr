"""Proprietes de la formule de Forbes-Rigobon, celles que la page affirme."""
import math

import pytest

from tools.contagion.bias import correction, delta_relatif, rho_conditionnelle


@pytest.mark.parametrize("rho", [-0.9, -0.3, 0.0, 0.2, 0.58, 0.95])
@pytest.mark.parametrize("delta", [-0.99, -0.5, 0.0, 1.0, 8.0])
def test_inversion_identite(rho, delta):
    assert correction(rho_conditionnelle(rho, delta), delta) == pytest.approx(rho, abs=1e-12)


def test_delta_nul_ne_change_rien():
    assert rho_conditionnelle(0.58, 0.0) == pytest.approx(0.58)


def test_limites():
    assert rho_conditionnelle(0.58, -1.0) == pytest.approx(0.0)
    assert rho_conditionnelle(0.58, 1e9) == pytest.approx(1.0, abs=1e-4)
    assert rho_conditionnelle(-0.58, 1e9) == pytest.approx(-1.0, abs=1e-4)


def test_monotone_en_delta():
    valeurs = [rho_conditionnelle(0.58, d) for d in (-0.9, -0.5, 0.0, 0.5, 2.0, 10.0)]
    assert all(a < b for a, b in zip(valeurs, valeurs[1:]))


def test_impaire_en_rho():
    assert rho_conditionnelle(-0.4, 2.0) == pytest.approx(-rho_conditionnelle(0.4, 2.0))


def test_delta_relatif():
    assert delta_relatif(2.0, 1.0) == pytest.approx(1.0)
    assert delta_relatif(0.5, 1.0) == pytest.approx(-0.5)


def test_points_fixes():
    for d in (-0.9, 0.0, 3.0):
        assert rho_conditionnelle(1.0, d) == pytest.approx(1.0, abs=1e-15)
        assert rho_conditionnelle(0.0, d) == 0.0


def test_bornee():
    for rho in (-0.9, -0.3, 0.0, 0.2, 0.58, 0.95):
        for d in (-0.99, -0.5, 0.0, 1.0, 8.0):
            assert abs(rho_conditionnelle(rho, d)) <= 1.0 + 1e-12
