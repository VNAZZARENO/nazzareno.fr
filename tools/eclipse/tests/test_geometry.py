import math
import pytest
from tools.eclipse.geometry import (
    angular_separation, disc_overlap_area, eclipse_magnitude, obscuration,
)


def test_separation_nulle_pour_deux_directions_identiques():
    assert angular_separation(120.0, 30.0, 120.0, 30.0) == pytest.approx(0.0, abs=1e-12)


def test_separation_petite_en_altitude():
    # deux points separes de 0.5 deg en altitude, meme azimut
    assert angular_separation(10.0, 30.0, 10.0, 30.5) == pytest.approx(0.5, abs=1e-9)


def test_separation_franchit_le_zero_azimut():
    # 359 deg et 1 deg sont separes de 2 deg, pas de 358
    assert angular_separation(359.0, 0.0, 1.0, 0.0) == pytest.approx(2.0, abs=1e-9)


def test_separation_symetrique():
    a = angular_separation(12.0, -3.0, 200.0, 61.0)
    b = angular_separation(200.0, 61.0, 12.0, -3.0)
    assert a == pytest.approx(b, abs=1e-12)


def test_disques_disjoints_sans_recouvrement():
    assert disc_overlap_area(3.0, 1.0, 1.0) == 0.0


def test_disque_petit_entierement_couvert():
    # la Lune (0.5) tient entierement dans le Soleil (1.0)
    assert disc_overlap_area(0.2, 1.0, 0.5) == pytest.approx(math.pi * 0.25)


def test_disques_egaux_concentriques():
    assert disc_overlap_area(0.0, 1.0, 1.0) == pytest.approx(math.pi)


def test_recouvrement_a_mi_chemin_est_entre_les_bornes():
    a = disc_overlap_area(1.0, 1.0, 1.0)
    assert 0.0 < a < math.pi


def test_magnitude_nulle_hors_eclipse():
    assert eclipse_magnitude(2.0, 1.0, 1.0) == 0.0


def test_magnitude_vaut_un_au_second_contact_de_taille_egale():
    assert eclipse_magnitude(0.0, 1.0, 1.0) == pytest.approx(1.0)


def test_magnitude_annulaire_inferieure_a_un():
    # Lune plus petite que le Soleil: annulaire, magnitude < 1 meme au maximum
    assert eclipse_magnitude(0.0, 1.0, 0.9) == pytest.approx(0.95)


def test_magnitude_totale_superieure_a_un():
    assert eclipse_magnitude(0.0, 1.0, 1.05) == pytest.approx(1.025)


def test_obscuration_nulle_hors_eclipse():
    assert obscuration(2.0, 1.0, 1.0) == 0.0


def test_obscuration_totale():
    assert obscuration(0.0, 1.0, 1.05) == pytest.approx(1.0)


def test_obscuration_annulaire_est_le_rapport_des_aires():
    # au maximum d'une annulaire, l'aire cachee est exactement (r_lune/r_soleil)^2
    assert obscuration(0.0, 1.0, 0.9) == pytest.approx(0.81)


def test_obscuration_decroit_avec_la_separation():
    valeurs = [obscuration(d, 1.0, 1.0) for d in (0.0, 0.5, 1.0, 1.5, 2.0)]
    assert all(a >= b for a, b in zip(valeurs, valeurs[1:]))
