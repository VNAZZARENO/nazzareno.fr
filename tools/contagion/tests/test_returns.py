"""Rendements et appariement: chaque affirmation du paragraphe methode."""
import numpy as np
import pytest

from tools.contagion.returns import (charger_cloture, paires, rendements_log,
                                     serie_appariee)


def test_rendements_log_sur_serie_jouet():
    dates = ["2020-01-01", "2020-01-02", "2020-01-03"]
    clotures = [100.0, 110.0, 99.0]
    d, r = rendements_log(dates, clotures)
    assert d == ["2020-01-02", "2020-01-03"]
    assert r[0] == pytest.approx(np.log(1.1))
    assert r[1] == pytest.approx(np.log(0.9))


def test_moyenne_mobile_2j():
    dates = ["2020-01-02", "2020-01-03", "2020-01-06"]
    r = np.array([0.01, 0.03, -0.02])
    d2, r2 = paires(dates, r)
    # moyenne du jour et de la veille SUR LE CALENDRIER PROPRE du marche
    assert d2 == ["2020-01-03", "2020-01-06"]
    assert r2[0] == pytest.approx(0.02)
    assert r2[1] == pytest.approx(0.005)


def test_appariement_sur_intersection():
    da, ra = ["2020-01-03", "2020-01-06", "2020-01-07"], np.array([1.0, 2.0, 3.0])
    db, rb = ["2020-01-03", "2020-01-07", "2020-01-08"], np.array([4.0, 5.0, 6.0])
    dates, xa, xb = serie_appariee(da, ra, db, rb)
    assert dates == ["2020-01-03", "2020-01-07"]
    assert list(xa) == [1.0, 3.0] and list(xb) == [4.0, 5.0]


def test_chaine_complete_sur_donnees_reelles():
    dates, rx, ry = charger_cloture()
    assert len(dates) > 6000                      # ~35 ans de jours communs
    assert not np.isnan(rx).any() and not np.isnan(ry).any()
    # la moyenne mobile 2 jours induit une autocorrelation MA(1) positive: declaree
    for r in (rx, ry):
        ac1 = np.corrcoef(r[:-1], r[1:])[0, 1]
        assert ac1 > 0.2, "l'autocorrelation MA(1) attendue n'est pas la"
