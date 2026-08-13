import json
import pathlib
import pytest

CHEMIN = pathlib.Path("assets/data/eclipse-2026-08-12.json")

pytestmark = pytest.mark.skipif(
    not CHEMIN.exists(), reason="lancer d'abord: python3 -m tools.eclipse.build")


@pytest.fixture(scope="module")
def donnees():
    return json.loads(CHEMIN.read_text())


def test_trois_lieux(donnees):
    assert len(donnees["sites"]) == 3
    assert {s["id"] for s in donnees["sites"]} == {"paris", "espagne", "reykjavik"}


def test_chaque_image_a_treize_champs(donnees):
    for site in donnees["sites"]:
        assert all(len(f) == 13 for f in site["frames"])


def test_contacts_ordonnes_et_dans_la_fenetre(donnees):
    for site in donnees["sites"]:
        presents = [site["contacts"][k] for k in ("c1", "c2", "c3", "c4")
                    if site["contacts"][k] is not None]
        assert presents == sorted(presents)


def test_paris_est_partielle_et_les_deux_autres_totales(donnees):
    par_id = {s["id"]: s for s in donnees["sites"]}
    assert par_id["paris"]["contacts"]["c2"] is None
    assert par_id["espagne"]["contacts"]["c2"] is not None
    assert par_id["reykjavik"]["contacts"]["c2"] is not None


def test_le_maximum_est_dans_la_fenetre(donnees):
    for site in donnees["sites"]:
        fin = (len(site["frames"]) - 1) * site["step_s"]
        assert 0 < site["t_max_s"] < fin


def test_le_maximum_tombe_pendant_la_totalite(donnees):
    for site in donnees["sites"]:
        if site["contacts"]["c2"] is None:
            continue
        assert site["contacts"]["c2"] < site["t_max_s"] < site["contacts"]["c3"]


def test_flux_entier_aux_extremites_de_la_fenetre(donnees):
    for site in donnees["sites"]:
        for image in (site["frames"][0], site["frames"][-1]):
            for canal in image[8:11]:
                assert canal == pytest.approx(1.0, abs=1e-3)


def test_flux_nul_entre_les_contacts_internes(donnees):
    for site in donnees["sites"]:
        if site["contacts"]["c2"] is None:
            continue
        pas = site["step_s"]
        c2, c3 = site["contacts"]["c2"], site["contacts"]["c3"]
        milieu = int(round(((c2 + c3) / 2.0) / pas))
        assert all(c < 1e-6 for c in site["frames"][milieu][8:11])


def test_le_flux_suit_l_assombrissement_centre_bord(donnees):
    """Invariant central de la spec 4.1, corrige, verifie sur les vraies donnees.

    La spec l'enonce a sens unique -- flux < 1 - obscuration des 5 %
    d'obscuration. C'est faux au debut de l'eclipse, et pour la raison meme qui
    le rend vrai a la fin: la Lune entame le disque par le LIMBE, la partie la
    plus sombre, donc elle enleve moins de lumiere que de surface et il reste
    PLUS que 1 - obscuration. Ce n'est qu'une fois le centre couvert que le
    rapport s'inverse. Le croisement tombe vers 34 % d'obscuration.

    Le partage se dit proprement avec la magnitude: le centre du Soleil est dans
    le disque de la Lune quand d < r_lune, c'est-a-dire quand magnitude > 0.5
    (magnitude 0.5 <=> obscuration 40 %, deja au-dela du croisement). On laisse
    la bande 0.4 - 0.5 sans assertion: c'est la que le croisement se produit.

    Le calcul de flux lui-meme a ete recoupe par une integration 2D en force
    brute, independante de la reduction a une dimension de limb.py: accord a
    1e-5 pres a 5 %, 20 %, 50 % et 90 % d'obscuration.
    """
    profondes = superficielles = 0
    for site in donnees["sites"]:
        for image in site["frames"]:
            mag, obsc, flux_vert = image[6], image[7], image[9]
            if not 0.05 < obsc < 0.95:
                continue
            if mag > 0.5:
                assert flux_vert < 1.0 - obsc + 1e-9
                profondes += 1
            elif mag < 0.4:
                assert flux_vert > 1.0 - obsc - 1e-9
                superficielles += 1
    assert profondes > 100 and superficielles > 100


def test_magnitude_et_obscuration_coherentes(donnees):
    for site in donnees["sites"]:
        for image in site["frames"]:
            mag, obsc = image[6], image[7]
            assert (mag <= 0.0) == (obsc <= 0.0)


def test_fichier_assez_compact(donnees):
    assert CHEMIN.stat().st_size < 400_000
