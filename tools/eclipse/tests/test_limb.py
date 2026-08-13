import pytest
from tools.eclipse.geometry import obscuration
from tools.eclipse.limb import intensity, visible_flux_fraction, SRGB_LIMB_COEFFS


def test_intensite_normalisee_au_centre():
    for u1, u2 in SRGB_LIMB_COEFFS:
        assert intensity(1.0, u1, u2) == pytest.approx(1.0)


def test_intensite_decroit_du_centre_vers_le_limbe():
    for u1, u2 in SRGB_LIMB_COEFFS:
        valeurs = [intensity(mu, u1, u2) for mu in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0)]
        assert all(a >= b for a, b in zip(valeurs, valeurs[1:]))


def test_rapport_limbe_centre_dans_la_plage_observee():
    # le limbe solaire vaut ~30-40 % du centre dans le visible
    for u1, u2 in SRGB_LIMB_COEFFS:
        assert 0.15 < intensity(0.0, u1, u2) < 0.55


def test_limbe_plus_rouge_que_le_centre():
    # SRGB_LIMB_COEFFS est ordonne (rouge, vert, bleu):
    # l'assombrissement est plus marque vers le bleu
    rouge, vert, bleu = (intensity(0.0, u1, u2) for u1, u2 in SRGB_LIMB_COEFFS)
    assert rouge > vert > bleu


def test_flux_entier_hors_eclipse():
    u1, u2 = SRGB_LIMB_COEFFS[1]
    assert visible_flux_fraction(2.0, 1.0, 1.0, u1, u2) == pytest.approx(1.0)


def test_flux_nul_en_totalite():
    u1, u2 = SRGB_LIMB_COEFFS[1]
    assert visible_flux_fraction(0.0, 1.0, 1.05, u1, u2) == pytest.approx(0.0, abs=1e-12)


def test_disque_uniforme_redonne_exactement_l_obscuration_geometrique():
    # u1 = u2 = 0 annule l'assombrissement: le flux doit alors coincider
    # avec 1 - obscuration. C'est le test qui valide l'integration elle-meme.
    for d in (0.2, 0.5, 0.9, 1.3, 1.8):
        attendu = 1.0 - obscuration(d, 1.0, 1.0)
        obtenu = visible_flux_fraction(d, 1.0, 1.0, 0.0, 0.0)
        assert obtenu == pytest.approx(attendu, abs=2e-4)


def test_le_flux_passe_sous_l_obscuration_geometrique_en_partielle_profonde():
    # LE point de la spec 4.1: le croissant residuel est au limbe, donc plus
    # sombre que la moyenne. Le flux tombe SOUS 1 - obscuration.
    u1, u2 = SRGB_LIMB_COEFFS[1]
    d = 0.35  # partielle profonde, disques de meme taille
    geometrique = 1.0 - obscuration(d, 1.0, 1.0)
    reel = visible_flux_fraction(d, 1.0, 1.0, u1, u2)
    assert 0.0 < reel < geometrique
    assert geometrique - reel > 0.01  # l'ecart est significatif, pas du bruit


def test_flux_croit_avec_la_separation():
    u1, u2 = SRGB_LIMB_COEFFS[1]
    valeurs = [visible_flux_fraction(d, 1.0, 1.0, u1, u2)
               for d in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0)]
    assert all(a <= b for a, b in zip(valeurs, valeurs[1:]))


def test_flux_insensible_au_pas_d_integration():
    u1, u2 = SRGB_LIMB_COEFFS[1]
    grossier = visible_flux_fraction(0.6, 1.0, 1.02, u1, u2, n=256)
    fin = visible_flux_fraction(0.6, 1.0, 1.02, u1, u2, n=4096)
    assert grossier == pytest.approx(fin, abs=1e-4)
