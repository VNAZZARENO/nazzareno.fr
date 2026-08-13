import pytest
from tools.eclipse.contacts import find_contacts


def separation_en_v(t):
    """Separation qui descend puis remonte, minimum 0.1 a t = 100."""
    return abs(t - 100.0) * 0.01 + 0.1


def separation_totale(t):
    """Minimum 0.0 a t = 100: la totalite a lieu."""
    return abs(t - 100.0) * 0.01


def test_contacts_exterieurs_symetriques_autour_du_minimum():
    c = find_contacts(separation_en_v, 0.0, 200.0, r_sun=0.26, r_moon=0.27)
    # C1 et C4 quand d = r_sun + r_moon = 0.53
    assert c["c1"] == pytest.approx(57.0, abs=1e-3)
    assert c["c4"] == pytest.approx(143.0, abs=1e-3)


def test_pas_de_contacts_internes_si_le_minimum_est_trop_grand():
    # minimum 0.1 > |r_sun - r_moon| = 0.01: pas de totalite
    c = find_contacts(separation_en_v, 0.0, 200.0, r_sun=0.26, r_moon=0.27)
    assert c["c2"] is None
    assert c["c3"] is None


def test_contacts_internes_presents_en_totalite():
    c = find_contacts(separation_totale, 0.0, 200.0, r_sun=0.26, r_moon=0.27)
    # C2 et C3 quand d = |r_sun - r_moon| = 0.01
    assert c["c2"] == pytest.approx(99.0, abs=1e-3)
    assert c["c3"] == pytest.approx(101.0, abs=1e-3)


def test_aucun_contact_si_les_disques_ne_se_touchent_jamais():
    c = find_contacts(lambda t: 5.0, 0.0, 200.0, r_sun=0.26, r_moon=0.27)
    assert all(v is None for v in c.values())


def test_les_contacts_sont_ordonnes():
    c = find_contacts(separation_totale, 0.0, 200.0, r_sun=0.26, r_moon=0.27)
    assert c["c1"] < c["c2"] < c["c3"] < c["c4"]


def test_totalite_plus_courte_que_le_pas_de_grille_est_detectee():
    # Totalite d'environ 4 s au milieu d'une fenetre de 8 h: bien plus courte
    # que le pas de la grille grossiere (28800/2000 = 14.4 s). Le centre est
    # place exactement entre deux echantillons de la grille (14400 + pas/2)
    # pour garantir qu'aucun echantillon ne tombe dans la fenetre de totalite:
    # sans raffinement du minimum, la grille enjambe la totalite et le calcul
    # repond faussement "partielle".
    centre = 14407.2

    def separation(t):
        return abs(t - centre) * 0.005
    c = find_contacts(separation, 0.0, 28800.0, r_sun=0.26, r_moon=0.27)
    assert c["c2"] is not None, "totalite courte ratee: minimum non raffine"
    assert c["c3"] is not None
    assert c["c2"] < centre < c["c3"]
