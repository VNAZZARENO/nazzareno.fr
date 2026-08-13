# Simulateur d'éclipse — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publier une page projet, en français et en anglais, qui restitue l'éclipse totale du 12 août 2026 vue simultanément depuis deux lieux, avec une géométrie calculée à partir des éphémérides JPL et un ciel rendu par un modèle de diffusion atmosphérique.

**Architecture:** Trois étages séparés par des interfaces étroites. Un script Python hors ligne calcule les éphémérides et écrit un JSON ; une page HTML statique reste entièrement utile à partir de ce seul JSON, sans WebGL ; un simulateur WebGL2 se greffe par-dessus en amélioration progressive. Le navigateur ne calcule aucune éphéméride.

**Tech Stack:** Python 3.12 + skyfield + DE440s + pytest (dans `.venv`, non versionné) · JavaScript ES modules natifs + WebGL2, zéro dépendance · `node --test` (intégré à Node 22) · aucune étape de build, aucun script tiers.

**Spec:** `docs/superpowers/specs/2026-08-13-simulateur-eclipse-design.md`

---

## Découpage en deux phases

La **phase 1** (tâches 1 à 12) produit un livrable complet et publiable : la page, dans les deux langues, avec les vrais chiffres de l'éclipse et le tableau des contacts, intégrée au site. Elle n'affiche aucun pixel de WebGL et reste parfaitement utile.

La **phase 2** (tâches 13 à 24) ajoute le simulateur par-dessus, en amélioration progressive.

Cet ordre est délibéré : il garantit que le repli sans WebGL fonctionne réellement, au lieu d'être rajouté après coup et jamais testé.

## Structure des fichiers

### Outillage hors ligne — `tools/eclipse/`

| Fichier | Responsabilité |
|---|---|
| `requirements.txt` | skyfield, numpy, scipy, pytest |
| `geometry.py` | séparation angulaire, aire d'intersection de deux disques, magnitude, obscuration. **Pur** : pas de skyfield, pas d'entrées-sorties |
| `limb.py` | assombrissement centre-bord et fraction de flux visible. **Pur** |
| `ephemeris.py` | enveloppe skyfield : un lieu et une grille de temps donnent une série d'états |
| `contacts.py` | recherche des instants C1 à C4 par recherche de racine |
| `sky_objects.py` | planètes et étoiles brillantes visibles au maximum |
| `build.py` | orchestration, écriture de `assets/data/eclipse-2026-08-12.json` |
| `validate.py` | comparaison aux valeurs publiées NASA, écriture de `VALIDATION.md` |
| `export_flux_lut.py` | export de valeurs de référence pour le test de conformité du JS |
| `NASA-REFERENCE.md` | les valeurs publiées, recopiées avec leur source |
| `VALIDATION.md` | rapport de validation, versionné |
| `tests/` | `test_geometry.py`, `test_limb.py`, `test_contacts.py`, `test_build.py` |

Le découpage sépare le **pur** (`geometry`, `limb` — testables sans réseau ni éphéméride) de l'**impur** (`ephemeris`, `sky_objects` — dépendants de DE440s). C'est ce qui rend la majorité du calcul testable en une milliseconde.

### Tests JavaScript — `tools/js-tests/`

`data.test.js`, `flux.test.js`, `fixture-eclipse.json`, `flux-reference.json`. Exécutés par `node --test tools/js-tests/`.

### Runtime — `assets/js/eclipse/`

| Fichier | Responsabilité | Dépend de |
|---|---|---|
| `data.js` | chargement du JSON, interpolation de l'état à l'instant `t` | — |
| `flux.js` | miroir JS de `limb.py`, pour construire la LUT flux↔séparation | — |
| `gl.js` | outillage WebGL2 : compilation, quad, textures, cibles de rendu | — |
| `atmosphere.glsl.js` | fragments GLSL partagés : densités, transmittance, fraction de flux | — |
| `sky.glsl.js` | source du shader de ciel | `atmosphere.glsl.js` |
| `inset.glsl.js` | source du shader de l'encart téléobjectif | — |
| `luts.js` | construction des trois LUT | `gl.js`, `flux.js` |
| `sky.js` | passe ciel : uniformes et dessin d'un panneau | `gl.js`, `luts.js`, `sky.glsl.js` |
| `inset.js` | passe téléobjectif | `gl.js`, `inset.glsl.js` |
| `ui.js` | frise, sélecteurs, balayage du regard, `aria-live`, clavier | `data.js` |
| `main.js` | câblage, boucle `rAF`, drapeau `dirty`, observateurs | tous |

`sky.js` ignore ce qu'est une frise. `data.js` ignore ce qu'est WebGL. `ui.js` ignore ce qu'est un shader.

### Pages et intégration

Créés : `projets/eclipse.html`, `en/projects/eclipse.html`, `assets/data/eclipse-2026-08-12.json`, `assets/img/eclipse-poster.webp`, `assets/og/eclipse.jpg`, `assets/og/eclipse-en.jpg`.
Modifiés : `index.html`, `en/index.html`, `sitemap.xml`, `assets/style.css`, `.gitignore`.

---

# Phase 1 — Les chiffres et la page

## Task 1: Environnement Python et éphéméride JPL

**Files:**
- Create: `tools/eclipse/requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Écrire `tools/eclipse/requirements.txt`**

```
skyfield==1.49
numpy>=1.26
scipy>=1.11
pytest>=8.0
```

- [ ] **Step 2: Ignorer le venv et les éphémérides binaires**

Ajouter à la fin de `.gitignore` :

```
.venv/
*.bsp
__pycache__/
.pytest_cache/
```

- [ ] **Step 3: Créer le venv et installer**

```bash
python3 -m venv .venv
source .venv/bin/activate && pip install -q -r tools/eclipse/requirements.txt
```

- [ ] **Step 4: Vérifier que DE440s se charge et donne une position plausible**

```bash
source .venv/bin/activate && python3 -c "
from skyfield.api import load, wgs84
eph = load('de440s.bsp'); ts = load.timescale()
t = ts.utc(2026, 8, 12, 18, 0, 0)
site = eph['earth'] + wgs84.latlon(48.8566, 2.3522)
alt, az, dist = site.at(t).observe(eph['sun']).apparent().altaz()
print(f'Soleil depuis Paris: alt={alt.degrees:.3f} az={az.degrees:.3f} d={dist.km:.0f} km')
"
```

Attendu : le téléchargement de `de440s.bsp` (~32 Mo) au premier appel, puis une altitude solaire positive de l'ordre de 20 à 40°, un azimut vers l'ouest (250–290°), une distance proche de 1,51·10⁸ km (le 12 août, la Terre est près de l'aphélie). Si l'altitude est négative ou la distance hors de l'intervalle 1,4–1,6·10⁸ km, arrêter : quelque chose ne va pas.

- [ ] **Step 5: Commit**

```bash
git add tools/eclipse/requirements.txt .gitignore
git commit -m "Outillage Python pour le calcul de l'eclipse"
```

---

## Task 2: Géométrie des disques (TDD)

Module pur : aucune éphéméride, aucune entrée-sortie. C'est là que vit la définition de la magnitude et de l'obscuration.

**Files:**
- Create: `tools/eclipse/geometry.py`
- Test: `tools/eclipse/tests/test_geometry.py`

- [ ] **Step 1: Écrire les tests qui échouent**

`tools/eclipse/tests/test_geometry.py` :

```python
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
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/test_geometry.py -q
```

Attendu : `ModuleNotFoundError: No module named 'tools.eclipse.geometry'`.

- [ ] **Step 3: Écrire `tools/eclipse/geometry.py`**

```python
"""Geometrie de deux disques apparents. Pur: pas d'ephemeride, pas d'E/S.

Toutes les grandeurs angulaires sont en degres.
"""

import math

__all__ = [
    "angular_separation", "disc_overlap_area", "eclipse_magnitude", "obscuration",
]


def angular_separation(az1, alt1, az2, alt2):
    """Separation angulaire entre deux directions du ciel, en degres.

    Formule de Vincenty: contrairement a acos(produit scalaire), elle reste
    precise aux tres petits angles, ce qui est exactement le regime d'une
    eclipse (quelques minutes d'arc autour du contact).
    """
    a1, d1, a2, d2 = map(math.radians, (az1, alt1, az2, alt2))
    da = a2 - a1
    num = math.hypot(
        math.cos(d2) * math.sin(da),
        math.cos(d1) * math.sin(d2) - math.sin(d1) * math.cos(d2) * math.cos(da),
    )
    den = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(da)
    return math.degrees(math.atan2(num, den))


def disc_overlap_area(d, r1, r2):
    """Aire d'intersection de deux disques de rayons r1 et r2 distants de d.

    Somme de deux segments circulaires. L'ecriture r^2*(a - sin(2a)/2) est
    preferee a la formule a racine carree: elle evite une annulation
    catastrophique quand les disques sont presque tangents.
    """
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = math.acos(max(-1.0, min(1.0, (d * d + r1 * r1 - r2 * r2) / (2.0 * d * r1))))
    a2 = math.acos(max(-1.0, min(1.0, (d * d + r2 * r2 - r1 * r1) / (2.0 * d * r2))))
    return r1 * r1 * (a1 - math.sin(2 * a1) / 2.0) + r2 * r2 * (a2 - math.sin(2 * a2) / 2.0)


def eclipse_magnitude(d, r_sun, r_moon):
    """Fraction du DIAMETRE solaire couverte. Convention usuelle:
    0 hors eclipse, 1 au contact interne quand les disques sont egaux,
    < 1 au maximum d'une annulaire, > 1 pour une totale.
    """
    if d >= r_sun + r_moon:
        return 0.0
    return (r_sun + r_moon - d) / (2.0 * r_sun)


def obscuration(d, r_sun, r_moon):
    """Fraction de l'AIRE du disque solaire couverte, entre 0 et 1.

    A ne pas confondre avec la fraction de flux (voir limb.py): l'aire ignore
    l'assombrissement centre-bord.
    """
    return disc_overlap_area(d, r_sun, r_moon) / (math.pi * r_sun * r_sun)
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/test_geometry.py -q
```

Attendu : `16 passed`.

- [ ] **Step 5: Commit**

```bash
git add tools/eclipse/geometry.py tools/eclipse/tests/test_geometry.py
git commit -m "Geometrie des disques: separation, magnitude, obscuration"
```

---

## Task 3: Assombrissement centre-bord et fraction de flux (TDD)

C'est le module le plus important du projet. Il encode la correction de physique du §4.1 de la spec : le flux résiduel passe **sous** `1 − obscuration`, parce que le croissant restant est au limbe.

**Files:**
- Create: `tools/eclipse/limb.py`
- Test: `tools/eclipse/tests/test_limb.py`

- [ ] **Step 1: Sourcer les coefficients d'assombrissement centre-bord**

Ne pas inventer de nombres. Utiliser la loi quadratique `I(mu)/I(1) = 1 - u1*(1-mu) - u2*(1-mu)^2` et prendre `u1`, `u2` pour trois longueurs d'onde proches des primaires sRGB (≈ 610, 550, 470 nm) dans une source citable — Pierce & Slaughter (1977) ou Neckel & Labs (1994) sont les tables solaires de référence.

Créer `tools/eclipse/NASA-REFERENCE.md` et y consigner, avec la référence bibliographique complète, les coefficients retenus. Ce fichier servira aussi à la tâche 6.

Contrainte de vérification, indépendante de la source : le rapport limbe/centre du Soleil dans le visible vaut environ **0,3 à 0,4** vers 550 nm, et il **décroît avec la longueur d'onde** (le limbe est plus rouge que le centre). Si les coefficients choisis ne reproduisent pas cela, ils sont mal recopiés.

- [ ] **Step 2: Écrire les tests qui échouent**

`tools/eclipse/tests/test_limb.py` :

```python
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
```

- [ ] **Step 3: Vérifier que les tests échouent**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/test_limb.py -q
```

Attendu : `ModuleNotFoundError: No module named 'tools.eclipse.limb'`.

- [ ] **Step 4: Écrire `tools/eclipse/limb.py`**

Remplacer les trois couples de `SRGB_LIMB_COEFFS` par les valeurs sourcées à l'étape 1.

```python
"""Assombrissement centre-bord du Soleil et fraction de flux non occultee.

Module pur. Voir NASA-REFERENCE.md pour la source des coefficients.

Le point physique, souvent mal enonce: pendant une partielle profonde la Lune
couvre le CENTRE du disque et ne laisse qu'un croissant au LIMBE, qui est la
partie la plus sombre. Le flux residuel passe donc SOUS la valeur naive
1 - obscuration. Ce qui fait qu'une partielle a 90 % se vit comme du plein
jour n'est pas la, mais dans la reponse logarithmique de l'oeil.
"""

import math

__all__ = ["intensity", "visible_flux_fraction", "SRGB_LIMB_COEFFS"]

# Loi quadratique I(mu)/I(1) = 1 - u1 (1-mu) - u2 (1-mu)^2,
# aux longueurs d'onde des primaires sRGB, dans l'ordre (rouge, vert, bleu).
# Source: voir NASA-REFERENCE.md.
SRGB_LIMB_COEFFS = (
    (0.00, 0.00),  # rouge  ~610 nm  <- remplacer par les valeurs sourcees
    (0.00, 0.00),  # vert   ~550 nm  <- remplacer par les valeurs sourcees
    (0.00, 0.00),  # bleu   ~470 nm  <- remplacer par les valeurs sourcees
)


def intensity(mu, u1, u2):
    """Intensite specifique normalisee, mu = cos(angle depuis le centre du disque).

    mu = 1 au centre du disque, mu = 0 au limbe.
    """
    v = 1.0 - mu
    return 1.0 - u1 * v - u2 * v * v


def visible_flux_fraction(d, r_sun, r_moon, u1, u2, n=2048):
    """Fraction du flux solaire non occultee, ponderee par l'assombrissement.

    L'integrale sur le disque est reduite a une dimension: pour un anneau de
    rayon rho, la Lune en masque un arc dont le demi-angle vaut
    acos((rho^2 + d^2 - r_moon^2) / (2 rho d)). La fraction visible de
    l'anneau est donc 1 - arc/pi, sans aucune integration angulaire.
    """
    if d >= r_sun + r_moon:
        return 1.0

    total = 0.0
    visible = 0.0
    for i in range(n):
        rho = (i + 0.5) / n * r_sun
        mu = math.sqrt(max(0.0, 1.0 - (rho / r_sun) ** 2))
        poids = intensity(mu, u1, u2) * rho
        total += poids

        if d <= 0.0:
            fraction = 0.0 if rho < r_moon else 1.0
        else:
            c = (rho * rho + d * d - r_moon * r_moon) / (2.0 * rho * d)
            if c >= 1.0:
                fraction = 1.0      # l'anneau est entierement hors de la Lune
            elif c <= -1.0:
                fraction = 0.0      # l'anneau est entierement dans la Lune
            else:
                fraction = 1.0 - math.acos(c) / math.pi
        visible += poids * fraction

    return visible / total


def rgb_flux_fraction(d, r_sun, r_moon, n=2048):
    """Fraction de flux visible sur les trois canaux, dans l'ordre (r, v, b)."""
    return tuple(
        visible_flux_fraction(d, r_sun, r_moon, u1, u2, n=n)
        for u1, u2 in SRGB_LIMB_COEFFS
    )
```

- [ ] **Step 5: Vérifier que les tests passent**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/test_limb.py -q
```

Attendu : `10 passed`. Si `test_disque_uniforme...` échoue, l'intégrale est fausse — la corriger avant tout le reste, car la tâche 15 en dépend directement. Si `test_rapport_limbe_centre...` ou `test_limbe_plus_rouge...` échoue, ce sont les coefficients de l'étape 1 qui sont mal recopiés.

- [ ] **Step 6: Commit**

```bash
git add tools/eclipse/limb.py tools/eclipse/tests/test_limb.py tools/eclipse/NASA-REFERENCE.md
git commit -m "Assombrissement centre-bord et fraction de flux par canal"
```

---

## Task 4: Enveloppe skyfield

**Files:**
- Create: `tools/eclipse/ephemeris.py`

Pas de TDD ici : ce module ne fait qu'appeler skyfield, et le tester reviendrait à tester skyfield. Sa correction est vérifiée à la tâche 6, contre les valeurs publiées.

- [ ] **Step 1: Écrire `tools/eclipse/ephemeris.py`**

```python
"""Enveloppe skyfield: un lieu et une grille de temps donnent une serie d'etats.

Seul module a dependre de DE440s. Tout le reste du calcul est pur.
"""

import math
from dataclasses import dataclass

from skyfield.api import load, wgs84

R_SUN_KM = 695_700.0
R_MOON_KM = 1_737.4

# Conditions standard pour la refraction. Elles ne changent pas la geometrie,
# seulement l'altitude apparente -- ce qui compte en Espagne ou le Soleil frise
# l'horizon.
TEMPERATURE_C = 15.0
PRESSURE_MBAR = 1013.25


@dataclass(frozen=True)
class Site:
    id: str
    name_fr: str
    name_en: str
    lat: float
    lon: float
    elevation_m: float
    tz: str


@dataclass(frozen=True)
class State:
    """Etat instantane vu depuis un lieu. Angles en degres, distances en km."""
    sun_az: float
    sun_alt: float
    moon_az: float
    moon_alt: float
    r_sun: float      # rayon angulaire apparent du Soleil
    r_moon: float     # rayon angulaire apparent de la Lune
    d_sun_km: float
    d_moon_km: float


def open_ephemeris(name="de440s.bsp"):
    """Charge l'ephemeride JPL et l'echelle de temps. Telecharge au besoin."""
    eph = load(name)
    return eph, load.timescale()


def observer(eph, site):
    return eph["earth"] + wgs84.latlon(site.lat, site.lon, elevation_m=site.elevation_m)


def state_at(eph, obs, t):
    """Etat topocentrique apparent, refraction comprise."""
    sun = obs.at(t).observe(eph["sun"]).apparent()
    moon = obs.at(t).observe(eph["moon"]).apparent()

    sun_alt, sun_az, sun_dist = sun.altaz(
        temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)
    moon_alt, moon_az, moon_dist = moon.altaz(
        temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)

    return State(
        sun_az=sun_az.degrees,
        sun_alt=sun_alt.degrees,
        moon_az=moon_az.degrees,
        moon_alt=moon_alt.degrees,
        r_sun=math.degrees(math.asin(R_SUN_KM / sun_dist.km)),
        r_moon=math.degrees(math.asin(R_MOON_KM / moon_dist.km)),
        d_sun_km=sun_dist.km,
        d_moon_km=moon_dist.km,
    )
```

- [ ] **Step 2: Vérifier sur un cas connu**

```bash
source .venv/bin/activate && python3 -c "
from tools.eclipse.ephemeris import *
eph, ts = open_ephemeris()
s = Site('paris','Paris','Paris',48.8566,2.3522,35,'Europe/Paris')
st = state_at(eph, observer(eph, s), ts.utc(2026,8,12,18,30,0))
print(st)
print('rayons apparents en degres:', round(st.r_sun,4), round(st.r_moon,4))
"
```

Attendu : des rayons apparents proches de 0,262° pour le Soleil et 0,25–0,28° pour la Lune (soit des diamètres d'environ un demi-degré, ce qui est la valeur bien connue). Si les rayons sortent de 0,2–0,3°, la conversion est fausse.

- [ ] **Step 3: Commit**

```bash
git add tools/eclipse/ephemeris.py
git commit -m "Enveloppe skyfield: etats topocentriques apparents"
```

---

## Task 5: Recherche des instants de contact (TDD)

**Files:**
- Create: `tools/eclipse/contacts.py`
- Test: `tools/eclipse/tests/test_contacts.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Les tests utilisent une fonction de séparation analytique — pas d'éphéméride — pour vérifier la recherche de racine elle-même.

`tools/eclipse/tests/test_contacts.py` :

```python
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
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/test_contacts.py -q
```

Attendu : `ModuleNotFoundError: No module named 'tools.eclipse.contacts'`.

- [ ] **Step 3: Écrire `tools/eclipse/contacts.py`**

```python
"""Recherche des instants de contact C1 a C4 par recherche de racine.

`separation` est une fonction du temps (en secondes depuis une origine
arbitraire) qui rend la separation angulaire en degres. Le module ne sait rien
des ephemerides: c'est ce qui le rend testable avec des fonctions analytiques.
"""

from scipy.optimize import brentq

__all__ = ["find_contacts"]


def _minimum_grossier(separation, t0, t1, n=2000):
    pas = (t1 - t0) / n
    t_min, d_min = t0, separation(t0)
    for i in range(1, n + 1):
        t = t0 + i * pas
        d = separation(t)
        if d < d_min:
            t_min, d_min = t, d
    return t_min, d_min


def _racine(separation, cible, a, b):
    """Racine de separation(t) = cible sur [a, b], ou None si pas d'encadrement."""
    fa = separation(a) - cible
    fb = separation(b) - cible
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        return None
    return brentq(lambda t: separation(t) - cible, a, b, xtol=1e-6)


def find_contacts(separation, t0, t1, r_sun, r_moon):
    """Rend {'c1','c2','c3','c4'} en secondes, valeurs None si le contact
    n'a pas lieu.

    C1 et C4: d = r_sun + r_moon (contacts exterieurs).
    C2 et C3: d = |r_sun - r_moon| (contacts interieurs, totalite ou annulaire).
    """
    t_min, d_min = _minimum_grossier(separation, t0, t1)

    externe = r_sun + r_moon
    interne = abs(r_sun - r_moon)

    contacts = {"c1": None, "c2": None, "c3": None, "c4": None}
    if d_min >= externe:
        return contacts

    contacts["c1"] = _racine(separation, externe, t0, t_min)
    contacts["c4"] = _racine(separation, externe, t_min, t1)
    if d_min < interne:
        contacts["c2"] = _racine(separation, interne, t0, t_min)
        contacts["c3"] = _racine(separation, interne, t_min, t1)
    return contacts
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/test_contacts.py -q
```

Attendu : `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add tools/eclipse/contacts.py tools/eclipse/tests/test_contacts.py
git commit -m "Recherche des instants de contact C1 a C4"
```

---

## Task 6: Valeurs publiées de référence

Cette tâche existe pour une seule raison : rendre l'affirmation « vrai » vérifiable par un lecteur. Elle doit être faite **avant** de produire le JSON, pour que le calcul soit confronté à une référence choisie à l'avance et non ajustée après coup.

**Files:**
- Modify: `tools/eclipse/NASA-REFERENCE.md`

- [ ] **Step 1: Relever les valeurs publiées**

Consulter le catalogue d'éclipses du NASA GSFC (Espenak) pour l'éclipse solaire totale du 12 août 2026, et consigner dans `NASA-REFERENCE.md` :

- l'instant du maximum général (« greatest eclipse ») en UTC ;
- la durée maximale de totalité ;
- pour **Paris**, **Reykjavík** et la ville espagnole retenue : les instants C1, C2, C3, C4 en UTC, la magnitude et l'obscuration au maximum, et l'altitude solaire au maximum.

Recopier la source exacte (URL et date de consultation) en tête du fichier. Si une valeur n'est pas publiée pour un lieu, l'écrire explicitement plutôt que de laisser une case vide.

- [ ] **Step 2: Arrêter la ville espagnole**

Critère de la spec §7 : totalité franche, altitude solaire la plus basse possible. Départager les candidates (Oviedo, Burgos, Palencia, Valence, Palma) sur les valeurs publiées, et consigner en une phrase la raison du choix dans `NASA-REFERENCE.md`.

- [ ] **Step 3: Commit**

```bash
git add tools/eclipse/NASA-REFERENCE.md
git commit -m "Valeurs publiees de reference pour l'eclipse du 12 aout 2026"
```

---

## Task 7: Objets du ciel visibles pendant la totalité

**Files:**
- Create: `tools/eclipse/sky_objects.py`

- [ ] **Step 1: Écrire `tools/eclipse/sky_objects.py`**

```python
"""Planetes et etoiles brillantes visibles au maximum de l'eclipse.

Le catalogue Hipparcos est telecharge par skyfield. S'il est indisponible, on
se rabat sur les seules planetes et on le signale: mieux vaut une page qui
annonce ce qui manque qu'une page qui invente.
"""

from skyfield.api import Star, load
from skyfield.data import hipparcos

PLANETES = {
    "Mercure": "mercury", "Venus": "venus", "Mars": "mars",
    "Jupiter": "jupiter barycenter", "Saturne": "saturn barycenter",
}

MAGNITUDE_LIMITE = 3.0


def planetes_visibles(eph, obs, t):
    sortie = []
    for nom, cle in PLANETES.items():
        app = obs.at(t).observe(eph[cle]).apparent()
        alt, az, _ = app.altaz()
        if alt.degrees > 0.0:
            sortie.append({"name": nom, "az": round(az.degrees, 3),
                           "alt": round(alt.degrees, 3)})
    return sortie


def etoiles_visibles(obs, t):
    """Etoiles plus brillantes que MAGNITUDE_LIMITE et au-dessus de l'horizon.

    Rend (liste, catalogue_disponible).
    """
    try:
        with load.open(hipparcos.URL) as f:
            df = hipparcos.load_dataframe(f)
    except Exception:
        return [], False

    df = df[df["magnitude"] <= MAGNITUDE_LIMITE]
    df = df[df["ra_degrees"].notna()]

    sortie = []
    for hip, ligne in df.iterrows():
        app = obs.at(t).observe(Star.from_dataframe(ligne)).apparent()
        alt, az, _ = app.altaz()
        if alt.degrees > 0.0:
            sortie.append({"hip": int(hip), "mag": round(float(ligne["magnitude"]), 2),
                           "az": round(az.degrees, 3), "alt": round(alt.degrees, 3)})
    sortie.sort(key=lambda e: e["mag"])
    return sortie, True
```

- [ ] **Step 2: Vérifier**

```bash
source .venv/bin/activate && python3 -c "
from tools.eclipse.ephemeris import *
from tools.eclipse.sky_objects import *
eph, ts = open_ephemeris()
s = Site('paris','Paris','Paris',48.8566,2.3522,35,'Europe/Paris')
obs = observer(eph, s); t = ts.utc(2026,8,12,18,30,0)
print('planetes:', planetes_visibles(eph, obs, t))
et, ok = etoiles_visibles(obs, t)
print('catalogue disponible:', ok, '| etoiles:', len(et), '| plus brillante:', et[0] if et else None)
"
```

Attendu : quelques planètes, et si le catalogue est joignable, quelques dizaines d'étoiles avec une magnitude minimale négative ou proche de zéro (Véga, Arcturus, Altaïr sont au-dessus de l'horizon depuis Paris en août au soir).

- [ ] **Step 3: Commit**

```bash
git add tools/eclipse/sky_objects.py
git commit -m "Planetes et etoiles brillantes au maximum de l'eclipse"
```

---

## Task 8: Assemblage et écriture du JSON (TDD sur les invariants)

**Files:**
- Create: `tools/eclipse/build.py`
- Test: `tools/eclipse/tests/test_build.py`

- [ ] **Step 1: Écrire les tests d'invariants qui échouent**

Ces tests portent sur le JSON réellement produit : ils sont lents mais ce sont eux qui attrapent une erreur de bout en bout.

`tools/eclipse/tests/test_build.py` :

```python
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


def test_le_flux_reste_sous_l_obscuration_geometrique(donnees):
    # invariant central de la spec 4.1, verifie sur les vraies donnees
    for site in donnees["sites"]:
        for image in site["frames"]:
            obsc, flux_vert = image[7], image[9]
            if 0.05 < obsc < 0.95:
                assert flux_vert < 1.0 - obsc + 1e-9


def test_magnitude_et_obscuration_coherentes(donnees):
    for site in donnees["sites"]:
        for image in site["frames"]:
            mag, obsc = image[6], image[7]
            assert (mag <= 0.0) == (obsc <= 0.0)


def test_fichier_assez_compact(donnees):
    assert CHEMIN.stat().st_size < 400_000
```

- [ ] **Step 2: Vérifier que les tests sont ignorés (le JSON n'existe pas)**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/test_build.py -q
```

Attendu : `9 skipped`.

- [ ] **Step 3: Écrire `tools/eclipse/build.py`**

Renseigner `SITES` avec la ville espagnole arrêtée à la tâche 6.

```python
"""Assemble le calcul complet et ecrit assets/data/eclipse-2026-08-12.json.

Usage: source .venv/bin/activate && python3 -m tools.eclipse.build
"""

import json
import pathlib

from tools.eclipse import geometry, limb
from tools.eclipse.contacts import find_contacts
from tools.eclipse.ephemeris import Site, open_ephemeris, observer, state_at
from tools.eclipse.sky_objects import planetes_visibles, etoiles_visibles

SORTIE = pathlib.Path("assets/data/eclipse-2026-08-12.json")

PAS_S = 20
MARGE_S = 300           # 5 min de part et d'autre de C1 et C4
FENETRE_UTC = (2026, 8, 12, 14, 0, 0)   # debut de la recherche grossiere
DUREE_RECHERCHE_S = 8 * 3600

SITES = [
    Site("paris", "Paris", "Paris", 48.8566, 2.3522, 35.0, "Europe/Paris"),
    # <- ville arretee a la tache 6, avec ses vraies coordonnees
    Site("espagne", "", "", 0.0, 0.0, 0.0, "Europe/Madrid"),
    Site("reykjavik", "Reykjavík", "Reykjavík", 64.1466, -21.9426, 30.0,
         "Atlantic/Reykjavik"),
]


def _separation_fn(eph, obs, ts, t_origine):
    """Rend une fonction t(secondes depuis t_origine) -> separation en degres."""
    def separation(t_s):
        st = state_at(eph, obs, ts.tt_jd(t_origine.tt + t_s / 86400.0))
        return geometry.angular_separation(
            st.sun_az, st.sun_alt, st.moon_az, st.moon_alt)
    return separation


def construire_site(eph, ts, site):
    obs = observer(eph, site)
    t_origine = ts.utc(*FENETRE_UTC)
    separation = _separation_fn(eph, obs, ts, t_origine)

    # rayons apparents au milieu de la fenetre: ils varient de moins de 0.1 %
    # sur quelques heures, largement assez stable pour encadrer les contacts
    st_ref = state_at(eph, obs, ts.tt_jd(t_origine.tt + DUREE_RECHERCHE_S / 2 / 86400.0))
    contacts = find_contacts(separation, 0.0, DUREE_RECHERCHE_S,
                             st_ref.r_sun, st_ref.r_moon)
    if contacts["c1"] is None:
        raise SystemExit(f"aucune eclipse visible depuis {site.id}")

    debut = contacts["c1"] - MARGE_S
    fin = contacts["c4"] + MARGE_S
    n = int((fin - debut) / PAS_S) + 1

    images = []
    for i in range(n):
        t_s = debut + i * PAS_S
        st = state_at(eph, obs, ts.tt_jd(t_origine.tt + t_s / 86400.0))
        d = geometry.angular_separation(st.sun_az, st.sun_alt, st.moon_az, st.moon_alt)
        f_r, f_v, f_b = limb.rgb_flux_fraction(d, st.r_sun, st.r_moon, n=512)
        images.append([
            round(st.sun_az, 4), round(st.sun_alt, 4),
            round(st.moon_az, 4), round(st.moon_alt, 4),
            round(st.r_sun, 6), round(st.r_moon, 6),
            round(max(0.0, geometry.eclipse_magnitude(d, st.r_sun, st.r_moon)), 5),
            round(geometry.obscuration(d, st.r_sun, st.r_moon), 5),
            round(f_r, 6), round(f_v, 6), round(f_b, 6),
            round(st.d_sun_km, 1), round(st.d_moon_km, 3),
        ])

    t_max = (contacts["c1"] + contacts["c4"]) / 2.0
    t_max_jd = ts.tt_jd(t_origine.tt + t_max / 86400.0)
    etoiles, catalogue_ok = etoiles_visibles(obs, t_max_jd)

    def utc(t_s):
        if t_s is None:
            return None
        return ts.tt_jd(t_origine.tt + t_s / 86400.0).utc_iso()

    return {
        "id": site.id,
        "name_fr": site.name_fr, "name_en": site.name_en,
        "lat": site.lat, "lon": site.lon,
        "elevation_m": site.elevation_m, "tz": site.tz,
        "contacts": {k: utc(v) for k, v in contacts.items()},
        "t0_utc": utc(debut), "step_s": PAS_S,
        "frames": images,
        "sky_at_max": {
            "planets": planetes_visibles(eph, obs, t_max_jd),
            "stars": etoiles[:60],
            "star_catalogue_available": catalogue_ok,
        },
    }


def main():
    import skyfield
    eph, ts = open_ephemeris()
    sites = [construire_site(eph, ts, s) for s in SITES]
    document = {
        "eclipse": {"id": "2026-08-12",
                    "label_fr": "Éclipse totale de Soleil du 12 août 2026",
                    "label_en": "Total solar eclipse of 12 August 2026"},
        "source": {"ephemeris": "DE440s", "software": f"skyfield {skyfield.__version__}"},
        "sites": sites,
    }
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    for s in sites:
        print(f"{s['id']}: {len(s['frames'])} images, contacts {s['contacts']}")
    print(f"ecrit {SORTIE} ({SORTIE.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Produire le JSON**

```bash
source .venv/bin/activate && python3 -m tools.eclipse.build
```

Attendu : trois lignes de résumé, puis un fichier de l'ordre de 150 à 350 Ko avant compression.

- [ ] **Step 5: Vérifier les invariants**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/ -q
```

Attendu : tout passe. `test_le_flux_reste_sous_l_obscuration_geometrique` est le plus important : il confirme sur les vraies données la physique corrigée du §4.1.

- [ ] **Step 6: Commit**

```bash
git add tools/eclipse/build.py tools/eclipse/tests/test_build.py assets/data/eclipse-2026-08-12.json
git commit -m "Calcul complet de l'eclipse et donnees produites"
```

---

## Task 9: Rapport de validation contre les valeurs publiées

**Files:**
- Create: `tools/eclipse/validate.py`, `tools/eclipse/VALIDATION.md`

- [ ] **Step 1: Écrire `tools/eclipse/validate.py`**

Renseigner `PUBLIE` avec les valeurs relevées à la tâche 6.

```python
"""Compare les valeurs calculees aux valeurs publiees et ecrit VALIDATION.md.

Usage: source .venv/bin/activate && python3 -m tools.eclipse.validate
"""

import json
import pathlib
from datetime import datetime

DONNEES = pathlib.Path("assets/data/eclipse-2026-08-12.json")
RAPPORT = pathlib.Path("tools/eclipse/VALIDATION.md")

TOLERANCE_CONTACT_S = 5.0
TOLERANCE_MAGNITUDE = 0.002

# Valeurs publiees, relevees a la tache 6. Voir NASA-REFERENCE.md pour la source.
PUBLIE = {
    "paris": {"c1": "...", "c4": "...", "magnitude": 0.0},
    "espagne": {"c1": "...", "c2": "...", "c3": "...", "c4": "...", "magnitude": 0.0},
    "reykjavik": {"c1": "...", "c2": "...", "c3": "...", "c4": "...", "magnitude": 0.0},
}


def _secondes(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def main():
    donnees = json.loads(DONNEES.read_text())
    lignes = [
        "# Validation du calcul",
        "",
        "Comparaison du calcul de `tools/eclipse/build.py` aux valeurs publiees",
        "consignees dans `NASA-REFERENCE.md`.",
        "",
        f"Tolerances: contacts {TOLERANCE_CONTACT_S} s, magnitude {TOLERANCE_MAGNITUDE}.",
        "",
        "| Lieu | Grandeur | Publie | Calcule | Ecart | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    tout_ok = True

    for site in donnees["sites"]:
        attendu = PUBLIE.get(site["id"], {})
        for cle in ("c1", "c2", "c3", "c4"):
            ref, obtenu = attendu.get(cle), site["contacts"].get(cle)
            if ref in (None, "...") or obtenu is None:
                continue
            ecart = _secondes(obtenu) - _secondes(ref)
            ok = abs(ecart) <= TOLERANCE_CONTACT_S
            tout_ok &= ok
            lignes.append(f"| {site['id']} | {cle.upper()} | {ref} | {obtenu} | "
                          f"{ecart:+.1f} s | {'ok' if ok else 'ECART'} |")

        if attendu.get("magnitude"):
            calculee = max(f[6] for f in site["frames"])
            ecart = calculee - attendu["magnitude"]
            ok = abs(ecart) <= TOLERANCE_MAGNITUDE
            tout_ok &= ok
            lignes.append(f"| {site['id']} | magnitude | {attendu['magnitude']:.4f} | "
                          f"{calculee:.4f} | {ecart:+.4f} | {'ok' if ok else 'ECART'} |")

    lignes += ["", f"**Verdict global : {'conforme' if tout_ok else 'ECARTS DETECTES'}**", ""]
    RAPPORT.write_text("\n".join(lignes))
    print("\n".join(lignes))
    raise SystemExit(0 if tout_ok else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lancer la validation**

```bash
source .venv/bin/activate && python3 -m tools.eclipse.validate
```

Attendu : code de sortie 0 et « conforme ». En cas d'écart, ne pas élargir la tolérance : chercher la cause. Les suspects, dans l'ordre de probabilité — la réfraction (`TEMPERATURE_C`, `PRESSURE_MBAR`), l'altitude du lieu, et le fait que les tables publiées donnent parfois les contacts pour un point précis de la bande plutôt que pour la ville.

- [ ] **Step 3: Commit**

```bash
git add tools/eclipse/validate.py tools/eclipse/VALIDATION.md
git commit -m "Rapport de validation contre les valeurs publiees"
```

---

## Task 10: La page française, sans WebGL

Livrable autonome : la page est complète et utile à ce stade.

**Files:**
- Create: `projets/eclipse.html`
- Modify: `assets/style.css`

- [ ] **Step 1: Écrire `projets/eclipse.html`**

Reprendre exactement la structure de `projets/donnees-en-image.html` : même `<head>`, même en-tête, même pied de page, `<body class="article">`, script GoatCounter final. Contenu propre à cette page :

- `<p class="kicker">Projet</p>`, un `<h1>`, un `<p class="standfirst">`.
- Un `<p class="facts">` avec les jalons : `skyfield`, `éphémérides JPL DE440s`, `WebGL2`, `sans dépendance`.
- Un conteneur `<div id="eclipse-sim" class="sim">` contenant, **en HTML statique** : une image `<img>` de repli (fichier créé à la tâche 23 ; pour l'instant, omettre la balise et laisser le conteneur vide) et le **tableau des contacts**, rempli à la main à partir de `VALIDATION.md`, dans un `<table class="contacts">`.
- Les sections rédigées : ce que montre la comparaison Paris / Espagne, l'assombrissement centre-bord (§4.1 de la spec, avec la distinction entre la chute du flux et l'adaptation de l'œil), l'ombre dans l'atmosphère et l'anneau de crépuscule.
- Une section **« Ce qui est calculé, ce qui est modélisé »** reprenant les quatre catégories du §6 de la spec, y compris l'exposition fixe du §4.5.
- Un lien vers `tools/eclipse/VALIDATION.md` sur GitHub, pour que le lecteur puisse vérifier.
- `<p class="backlink"><a href="/#projets">← retour aux projets</a></p>`.

Le tableau des contacts est le cœur du repli : il doit contenir C1 à C4, la magnitude et l'obscuration pour les trois lieux. C'est lui qui rend la page utile sans une ligne de JavaScript.

- [ ] **Step 2: Ajouter les styles du tableau dans `assets/style.css`**

À la fin du fichier, en suivant les conventions existantes (variables `--rule`, `--ink-soft`, `--mono`) :

```css
/* ---- simulateur d'eclipse ---- */

.sim {
  margin: 1.5rem 0;
}
table.contacts {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--mono);
  font-size: 0.8125rem;
  margin: 1rem 0;
}
table.contacts th,
table.contacts td {
  border-bottom: 1px solid var(--rule);
  padding: 0.5rem 0.6rem;
  text-align: right;
}
table.contacts th:first-child,
table.contacts td:first-child {
  text-align: left;
  font-family: var(--serif);
}
table.contacts thead th {
  color: var(--ink-soft);
  font-weight: 500;
}
table.contacts td.absent {
  color: var(--ink-soft);
}
```

- [ ] **Step 3: Vérifier dans un navigateur**

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Ouvrir `http://127.0.0.1:8000/projets/eclipse.html`. Vérifier : le tableau est lisible, la page suit la charte, et elle fonctionne en thème clair comme en thème sombre.

- [ ] **Step 4: Commit**

```bash
git add projets/eclipse.html assets/style.css
git commit -m "Page projet eclipse en francais, utilisable sans JavaScript"
```

---

## Task 11: La page anglaise

**Files:**
- Create: `en/projects/eclipse.html`

- [ ] **Step 1: Traduire la page**

Copier `projets/eclipse.html`, traduire le contenu, et corriger les liens croisés : `lang="en"`, `canonical` vers `/en/projects/eclipse.html`, `hreflang` réciproques, `og:image` vers `/assets/og/eclipse-en.jpg`, sélecteur de langue et pied de page pointant vers la version française. Prendre `en/projects/data-as-image.html` comme modèle exact de ces réglages.

- [ ] **Step 2: Ajouter le lien croisé dans la page française**

Dans `projets/eclipse.html`, vérifier que `hreflang="en"`, le sélecteur de langue de l'en-tête et le pied de page pointent bien vers `/en/projects/eclipse.html`.

- [ ] **Step 3: Vérifier**

Naviguer entre les deux pages via le sélecteur de langue de l'en-tête, dans les deux sens.

- [ ] **Step 4: Commit**

```bash
git add en/projects/eclipse.html projets/eclipse.html
git commit -m "Version anglaise de la page eclipse"
```

---

## Task 12: Intégration au site

**Files:**
- Modify: `index.html`, `en/index.html`, `sitemap.xml`

- [ ] **Step 1: Ajouter l'entrée dans la liste des projets française**

Dans `index.html`, section `#projets`, ajouter en **première** position de `<ul class="items">` (c'est le projet le plus récent) :

```html
      <li>
        <h3><a href="/projets/eclipse.html">Simulateur d'éclipse</a></h3>
        <p>L'éclipse totale du 12 août 2026 vue au même instant depuis Paris et depuis l'Espagne, avec une géométrie calculée sur les éphémérides JPL et un ciel rendu par diffusion atmosphérique.</p>
        <p class="more"><a href="/projets/eclipse.html">lire →</a></p>
      </li>
```

Attention : la règle CSS `.items li:first-child` supprime la bordure haute et réduit le rembourrage. En insérant en tête, vérifier visuellement que l'ancien premier élément reprend bien sa bordure.

- [ ] **Step 2: Ajouter l'entrée anglaise**

Même opération dans `en/index.html`, avec le texte traduit et le lien `/en/projects/eclipse.html`.

- [ ] **Step 3: Ajouter les deux URL au sitemap**

Dans `sitemap.xml`, en suivant exactement la forme des entrées existantes (`<loc>`, `<lastmod>` à la date du jour, et les `<xhtml:link>` réciproques si les autres entrées en ont).

- [ ] **Step 4: Vérifier**

Contrôler que le sitemap reste un XML valide :

```bash
python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse('sitemap.xml'); print('sitemap valide')"
```

Puis, depuis le serveur local, vérifier que les deux nouvelles entrées de la page d'accueil mènent aux bonnes pages.

- [ ] **Step 5: Commit**

```bash
git add index.html en/index.html sitemap.xml
git commit -m "Integrer la page eclipse au site et au sitemap"
```

**Fin de la phase 1.** La page est publiable en l'état : elle porte les vrais chiffres, elle est bilingue, accessible et intégrée.

---

# Phase 2 — Le simulateur

## Task 13: Couche de données côté navigateur (TDD)

**Files:**
- Create: `assets/js/eclipse/data.js`
- Test: `tools/js-tests/data.test.js`, `tools/js-tests/fixture-eclipse.json`

- [ ] **Step 1: Créer la fixture de test**

`tools/js-tests/fixture-eclipse.json` — données synthétiques réduites, uniquement pour les tests (jamais servies au site) :

```json
{
  "eclipse": {"id": "test", "label_fr": "test", "label_en": "test"},
  "source": {"ephemeris": "test", "software": "test"},
  "sites": [{
    "id": "essai", "name_fr": "Essai", "name_en": "Test",
    "lat": 0.0, "lon": 0.0, "elevation_m": 0.0, "tz": "UTC",
    "contacts": {"c1": "2026-08-12T17:00:00Z", "c2": null, "c3": null,
                 "c4": "2026-08-12T17:00:40Z"},
    "t0_utc": "2026-08-12T17:00:00Z", "step_s": 20,
    "frames": [
      [10.0, 30.0, 10.0, 29.0, 0.26, 0.27, 0.0, 0.0, 1.0, 1.0, 1.0, 1.5e8, 380000.0],
      [20.0, 32.0, 20.0, 31.0, 0.26, 0.27, 0.5, 0.4, 0.5, 0.5, 0.5, 1.5e8, 380000.0],
      [350.0, 34.0, 350.0, 33.0, 0.26, 0.27, 1.0, 1.0, 0.0, 0.0, 0.0, 1.5e8, 380000.0]
    ],
    "sky_at_max": {"planets": [], "stars": [], "star_catalogue_available": true}
  }]
}
```

- [ ] **Step 2: Écrire les tests qui échouent**

`tools/js-tests/data.test.js` :

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseEclipse, stateAt, windowSeconds } from '../../assets/js/eclipse/data.js';

const brut = JSON.parse(readFileSync(new URL('./fixture-eclipse.json', import.meta.url)));
const eclipse = parseEclipse(brut);
const site = eclipse.sites[0];

test('la fenetre couvre toutes les images', () => {
  assert.equal(windowSeconds(site), 40);
});

test('rend exactement la premiere image a t = 0', () => {
  const e = stateAt(site, 0);
  assert.equal(e.sunAlt, 30);
  assert.equal(e.fluxG, 1);
});

test('rend exactement la derniere image en fin de fenetre', () => {
  const e = stateAt(site, 40);
  assert.equal(e.sunAlt, 34);
  assert.equal(e.fluxG, 0);
});

test('interpole lineairement entre deux images', () => {
  const e = stateAt(site, 10);
  assert.equal(e.sunAlt, 31);
  assert.equal(e.fluxG, 0.75);
});

test("l'azimut prend le chemin le plus court a travers zero", () => {
  // de 20 deg a 350 deg: le chemin court passe par 5 deg, pas par 185 deg
  const e = stateAt(site, 30);
  assert.equal(e.sunAz, 5);
});

test('borne les temps hors fenetre au lieu d extrapoler', () => {
  assert.equal(stateAt(site, -100).sunAlt, 30);
  assert.equal(stateAt(site, 1e6).sunAlt, 34);
});

test('les contacts sont convertis en secondes depuis t0', () => {
  assert.equal(site.contacts.c1, 0);
  assert.equal(site.contacts.c4, 40);
  assert.equal(site.contacts.c2, null);
});
```

- [ ] **Step 3: Vérifier que les tests échouent**

```bash
node --test tools/js-tests/data.test.js
```

Attendu : `ERR_MODULE_NOT_FOUND` sur `data.js`.

- [ ] **Step 4: Écrire `assets/js/eclipse/data.js`**

```js
// Chargement et interpolation de la chronologie de l'eclipse.
// Ce module ignore tout de WebGL et du DOM: il ne fait que des maths sur un
// tableau de nombres, ce qui le rend testable sous node --test.

const CHAMPS = [
  'sunAz', 'sunAlt', 'moonAz', 'moonAlt', 'rSun', 'rMoon',
  'magnitude', 'obscuration', 'fluxR', 'fluxG', 'fluxB', 'dSunKm', 'dMoonKm',
];

// Index des champs qui sont des azimuts: ils s'interpolent par le chemin le
// plus court, sinon un passage par 360 deg produirait un demi-tour complet.
const AZIMUTS = new Set([0, 2]);

function secondesDepuis(t0Iso, iso) {
  if (iso === null || iso === undefined) return null;
  return (Date.parse(iso) - Date.parse(t0Iso)) / 1000;
}

export function parseEclipse(brut) {
  return {
    ...brut,
    sites: brut.sites.map((s) => ({
      ...s,
      t0Ms: Date.parse(s.t0_utc),
      contacts: Object.fromEntries(
        Object.entries(s.contacts).map(([k, v]) => [k, secondesDepuis(s.t0_utc, v)]),
      ),
    })),
  };
}

export async function loadEclipse(url) {
  const reponse = await fetch(url);
  if (!reponse.ok) throw new Error(`eclipse: HTTP ${reponse.status}`);
  return parseEclipse(await reponse.json());
}

export function windowSeconds(site) {
  return (site.frames.length - 1) * site.step_s;
}

function melangeAngle(a, b, k) {
  let delta = ((b - a + 540) % 360) - 180;   // ramene dans (-180, 180]
  return (a + delta * k + 360) % 360;
}

export function stateAt(site, secondes) {
  const duree = windowSeconds(site);
  const t = Math.min(Math.max(secondes, 0), duree);
  const position = t / site.step_s;
  const i = Math.min(Math.floor(position), site.frames.length - 2);
  const k = position - i;

  const a = site.frames[i];
  const b = site.frames[i + 1];
  const etat = { t };
  for (let c = 0; c < CHAMPS.length; c++) {
    etat[CHAMPS[c]] = AZIMUTS.has(c)
      ? melangeAngle(a[c], b[c], k)
      : a[c] + (b[c] - a[c]) * k;
  }
  return etat;
}
```

- [ ] **Step 5: Vérifier que les tests passent**

```bash
node --test tools/js-tests/data.test.js
```

Attendu : `pass 7`.

- [ ] **Step 6: Commit**

```bash
git add assets/js/eclipse/data.js tools/js-tests/data.test.js tools/js-tests/fixture-eclipse.json
git commit -m "Couche de donnees du simulateur: chargement et interpolation"
```

---

## Task 14: Miroir JavaScript du calcul de flux (TDD inter-langages)

La LUT flux↔séparation est construite dans le navigateur. Ce test garantit qu'elle donne les **mêmes valeurs** que Python — sinon l'atmosphère et l'observateur n'utiliseraient pas le même modèle, et le §4.2 de la spec s'effondrerait silencieusement.

**Files:**
- Create: `tools/eclipse/export_flux_lut.py`, `assets/js/eclipse/flux.js`
- Test: `tools/js-tests/flux.test.js`, `tools/js-tests/flux-reference.json`

- [ ] **Step 1: Écrire l'export des valeurs de référence**

`tools/eclipse/export_flux_lut.py` :

```python
"""Exporte des valeurs de reference de limb.py, pour verifier que le miroir
JavaScript calcule exactement la meme chose.

Usage: source .venv/bin/activate && python3 -m tools.eclipse.export_flux_lut
"""

import json
import pathlib

from tools.eclipse.limb import SRGB_LIMB_COEFFS, visible_flux_fraction

SORTIE = pathlib.Path("tools/js-tests/flux-reference.json")

CAS = [(d, ratio)
       for d in (0.0, 0.1, 0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 1.9, 2.05)
       for ratio in (0.92, 1.0, 1.05)]


def main():
    SORTIE.write_text(json.dumps({
        "coeffs": [list(c) for c in SRGB_LIMB_COEFFS],
        "n": 512,
        "cases": [
            {"d": d, "rMoon": ratio,
             "flux": [visible_flux_fraction(d, 1.0, ratio, u1, u2, n=512)
                      for u1, u2 in SRGB_LIMB_COEFFS]}
            for d, ratio in CAS
        ],
    }, indent=1))
    print(f"ecrit {SORTIE} ({len(CAS)} cas)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Produire les références**

```bash
source .venv/bin/activate && python3 -m tools.eclipse.export_flux_lut
```

Attendu : `ecrit tools/js-tests/flux-reference.json (30 cas)`.

- [ ] **Step 3: Écrire le test qui échoue**

`tools/js-tests/flux.test.js` :

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { visibleFluxFraction, buildFluxLut, LUT_D, LUT_RATIO } from '../../assets/js/eclipse/flux.js';

const ref = JSON.parse(readFileSync(new URL('./flux-reference.json', import.meta.url)));

test('le JS reproduit Python a 1e-9 pres', () => {
  for (const cas of ref.cases) {
    for (let c = 0; c < 3; c++) {
      const [u1, u2] = ref.coeffs[c];
      const obtenu = visibleFluxFraction(cas.d, 1.0, cas.rMoon, u1, u2, ref.n);
      assert.ok(Math.abs(obtenu - cas.flux[c]) < 1e-9,
        `d=${cas.d} rMoon=${cas.rMoon} canal=${c}: ${obtenu} vs ${cas.flux[c]}`);
    }
  }
});

test('la LUT a la bonne taille et reste dans [0, 1]', () => {
  const lut = buildFluxLut();
  assert.equal(lut.length, LUT_D * LUT_RATIO * 3);
  assert.ok(lut.every((v) => v >= 0 && v <= 1));
});

test('la LUT vaut 1 a separation maximale et 0 en totalite centrale', () => {
  const lut = buildFluxLut();
  const idx = (i, j, c) => (j * LUT_D + i) * 3 + c;
  // derniere colonne: separation la plus grande, donc hors eclipse
  assert.ok(lut[idx(LUT_D - 1, LUT_RATIO - 1, 1)] > 0.999);
  // premiere colonne, plus grand rapport de rayons: totalite centrale
  assert.ok(lut[idx(0, LUT_RATIO - 1, 1)] < 1e-6);
});
```

- [ ] **Step 4: Vérifier que le test échoue**

```bash
node --test tools/js-tests/flux.test.js
```

Attendu : `ERR_MODULE_NOT_FOUND` sur `flux.js`.

- [ ] **Step 5: Écrire `assets/js/eclipse/flux.js`**

Recopier `SRGB_LIMB_COEFFS` depuis `tools/eclipse/limb.py` — les deux doivent être identiques, et `flux.test.js` échoue si elles divergent.

```js
// Miroir JavaScript de tools/eclipse/limb.py.
// Sert a construire la LUT flux <-> separation dans le navigateur, plutot que
// de l'embarquer dans le JSON. Le test tools/js-tests/flux.test.js verifie que
// ce fichier rend exactement les memes valeurs que Python: si les deux
// divergent, l'atmosphere et l'observateur n'utilisent plus le meme modele.

// Ordre (rouge, vert, bleu). Doit rester identique a limb.py.
export const SRGB_LIMB_COEFFS = [
  [0.00, 0.00],
  [0.00, 0.00],
  [0.00, 0.00],
];

// Dimensions de la LUT: separation d / r_soleil, puis rapport r_lune / r_soleil.
export const LUT_D = 256;
export const LUT_RATIO = 32;
export const RATIO_MIN = 0.90;
export const RATIO_MAX = 1.10;
export const D_MAX = 2.2;          // au-dela, la fraction vaut 1 par construction

export function intensity(mu, u1, u2) {
  const v = 1 - mu;
  return 1 - u1 * v - u2 * v * v;
}

export function visibleFluxFraction(d, rSun, rMoon, u1, u2, n = 512) {
  if (d >= rSun + rMoon) return 1;

  let total = 0;
  let visible = 0;
  for (let i = 0; i < n; i++) {
    const rho = ((i + 0.5) / n) * rSun;
    const mu = Math.sqrt(Math.max(0, 1 - (rho / rSun) ** 2));
    const poids = intensity(mu, u1, u2) * rho;
    total += poids;

    let fraction;
    if (d <= 0) {
      fraction = rho < rMoon ? 0 : 1;
    } else {
      const c = (rho * rho + d * d - rMoon * rMoon) / (2 * rho * d);
      if (c >= 1) fraction = 1;
      else if (c <= -1) fraction = 0;
      else fraction = 1 - Math.acos(c) / Math.PI;
    }
    visible += poids * fraction;
  }
  return visible / total;
}

// Float32Array de LUT_D * LUT_RATIO * 3, ordonnee (ratio, d, canal).
export function buildFluxLut(n = 256) {
  const sortie = new Float32Array(LUT_D * LUT_RATIO * 3);
  for (let j = 0; j < LUT_RATIO; j++) {
    const ratio = RATIO_MIN + (RATIO_MAX - RATIO_MIN) * (j / (LUT_RATIO - 1));
    for (let i = 0; i < LUT_D; i++) {
      const d = D_MAX * (i / (LUT_D - 1));
      for (let c = 0; c < 3; c++) {
        const [u1, u2] = SRGB_LIMB_COEFFS[c];
        sortie[(j * LUT_D + i) * 3 + c] =
          visibleFluxFraction(d, 1.0, ratio, u1, u2, n);
      }
    }
  }
  return sortie;
}
```

- [ ] **Step 6: Vérifier que les tests passent**

```bash
node --test tools/js-tests/
```

Attendu : `pass 10` (7 de `data.test.js`, 3 de `flux.test.js`).

- [ ] **Step 7: Mesurer le coût de construction de la LUT**

```bash
node -e "
import('./assets/js/eclipse/flux.js').then(m => {
  const t = performance.now();
  m.buildFluxLut();
  console.log('LUT construite en', (performance.now()-t).toFixed(1), 'ms');
});
"
```

Attendu : moins de 100 ms. Au-delà, réduire `n` à 128 et relancer `flux.test.js` — la tolérance de `1e-9` porte sur `visibleFluxFraction` appelée avec `ref.n`, pas sur la LUT, donc le test reste valide.

- [ ] **Step 8: Commit**

```bash
git add tools/eclipse/export_flux_lut.py assets/js/eclipse/flux.js tools/js-tests/flux.test.js tools/js-tests/flux-reference.json
git commit -m "Miroir JS du calcul de flux, verifie contre Python"
```

---

## Task 15: Outillage WebGL2 et canvas piloté

Aucun rendu d'atmosphère ici : on met en place le canvas, la boucle et surtout le **drapeau `dirty`**, qui est le levier de performance principal de la spec §5.

**Files:**
- Create: `assets/js/eclipse/gl.js`, `assets/js/eclipse/main.js`
- Modify: `projets/eclipse.html`, `assets/style.css`

- [ ] **Step 1: Écrire `assets/js/eclipse/gl.js`**

```js
// Outillage WebGL2 minimal. Tout le rendu du simulateur tient dans des quads
// plein cadre: pas de geometrie, pas de matrices, pas de moteur.

export function createContext(canvas) {
  const gl = canvas.getContext('webgl2', {
    alpha: false, antialias: false, depth: false, stencil: false,
    powerPreference: 'low-power', preserveDrawingBuffer: false,
  });
  if (!gl) return null;
  if (!gl.getExtension('EXT_color_buffer_float')) return null;  // requis par les LUT
  return gl;
}

function compile(gl, type, source, nom) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(`${nom}: ${gl.getShaderInfoLog(shader)}`);
  }
  return shader;
}

const VERTEX_QUAD = `#version 300 es
void main() {
  // triangle unique couvrant le cadre, sans buffer de sommets
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;

export function createProgram(gl, fragmentSource, nom = 'programme') {
  const programme = gl.createProgram();
  gl.attachShader(programme, compile(gl, gl.VERTEX_SHADER, VERTEX_QUAD, `${nom}/vs`));
  gl.attachShader(programme, compile(gl, gl.FRAGMENT_SHADER, fragmentSource, `${nom}/fs`));
  gl.linkProgram(programme);
  if (!gl.getProgramParameter(programme, gl.LINK_STATUS)) {
    throw new Error(`${nom}: ${gl.getProgramInfoLog(programme)}`);
  }
  return programme;
}

export function drawQuad(gl) {
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}

export function createTexture(gl, largeur, hauteur, format, donnees = null) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texImage2D(gl.TEXTURE_2D, 0, format.internal, largeur, hauteur, 0,
                format.format, format.type, donnees);
  return tex;
}

export const RGBA16F = { internal: 0x881A, format: 0x1908, type: 0x140B };
export const RGB32F = { internal: 0x8815, format: 0x1907, type: 0x1406 };

export function renderToTexture(gl, tex, largeur, hauteur, dessiner) {
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  gl.viewport(0, 0, largeur, hauteur);
  dessiner();
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.deleteFramebuffer(fbo);
}
```

- [ ] **Step 2: Écrire `assets/js/eclipse/main.js` avec le drapeau `dirty`**

```js
// Cablage du simulateur. La regle qui gouverne ce fichier: on ne dessine
// QUE si quelque chose a change. Frise a l'arret et regard immobile
// signifient zero appel de dessin, donc zero CPU.

import { loadEclipse } from './data.js';
import { createContext } from './gl.js';

const CHEMIN_DONNEES = '/assets/data/eclipse-2026-08-12.json';

export async function init(racine) {
  const canvas = racine.querySelector('canvas');
  if (!canvas) return;

  const gl = createContext(canvas);
  if (!gl) return;                 // repli statique deja present dans le HTML

  const eclipse = await loadEclipse(CHEMIN_DONNEES);

  const etat = {
    gl, canvas, eclipse,
    tSecondes: 0,
    regardAz: 0,
    gauche: eclipse.sites.find((s) => s.id === 'paris'),
    droite: eclipse.sites.find((s) => s.id === 'espagne'),
    lecture: false,
    visible: true,
    sale: true,
  };

  const reduit = matchMedia('(prefers-reduced-motion: reduce)');
  etat.animationAutorisee = !reduit.matches;
  reduit.addEventListener('change', (e) => { etat.animationAutorisee = !e.matches; });

  new IntersectionObserver(([entree]) => {
    etat.visible = entree.isIntersecting;
    if (etat.visible) etat.sale = true;
  }, { threshold: 0.01 }).observe(canvas);

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) etat.sale = true;
  });

  redimensionner(etat);
  addEventListener('resize', () => { redimensionner(etat); });

  racine.dataset.webgl = 'ok';     // le CSS masque alors le repli statique
  boucle(etat);
  return etat;
}

function redimensionner(etat) {
  const echelle = Math.min(devicePixelRatio || 1, 1.5) * 0.7;
  const l = Math.round(etat.canvas.clientWidth * echelle);
  const h = Math.round(etat.canvas.clientHeight * echelle);
  if (l !== etat.canvas.width || h !== etat.canvas.height) {
    etat.canvas.width = l;
    etat.canvas.height = h;
    etat.sale = true;
  }
}

function boucle(etat) {
  const image = () => {
    if (etat.visible && !document.hidden) {
      if (etat.lecture && etat.animationAutorisee) {
        etat.tSecondes += 16 / 1000 * etat.vitesse;
        etat.sale = true;
      }
      if (etat.sale) {
        dessiner(etat);
        etat.sale = false;
      }
    }
    requestAnimationFrame(image);
  };
  requestAnimationFrame(image);
}

function dessiner(etat) {
  const { gl } = etat;
  gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
  gl.clearColor(0.04, 0.05, 0.07, 1.0);
  gl.clear(gl.COLOR_BUFFER_BIT);
}
```

- [ ] **Step 3: Ajouter le canvas et le module à la page**

Dans `projets/eclipse.html`, à l'intérieur de `<div id="eclipse-sim" class="sim">`, **avant** le tableau des contacts :

```html
    <canvas class="sim-canvas" width="1200" height="520"
            aria-label="Simulation du ciel pendant l'éclipse du 12 août 2026, vue depuis deux lieux."></canvas>
```

Et juste avant `</body>`, avant le script GoatCounter :

```html
<script type="module">
  import { init } from '/assets/js/eclipse/main.js';
  const racine = document.getElementById('eclipse-sim');
  if (racine) init(racine).catch((e) => console.warn('simulateur indisponible', e));
</script>
```

- [ ] **Step 4: Styler le canvas et le basculement du repli**

Dans `assets/style.css`, après le bloc `.sim` :

```css
.sim-canvas {
  display: none;
  width: 100%;
  height: auto;
  aspect-ratio: 12 / 5;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: #0c1018;
}
.sim[data-webgl="ok"] .sim-canvas {
  display: block;
}
.sim[data-webgl="ok"] .sim-fallback {
  display: none;
}
.sim-canvas:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 48rem) {
  .sim-canvas { aspect-ratio: 4 / 5; }
}
```

Envelopper l'image de repli et le tableau des contacts dans `<div class="sim-fallback">`, de sorte que le tableau reste visible même quand WebGL fonctionne — **non** : garder le tableau **hors** de `.sim-fallback`. Le tableau est une information utile en permanence, seule l'image poster doit disparaître quand le simulateur tourne.

- [ ] **Step 5: Vérifier**

Servir le site, ouvrir la page. Attendu : un rectangle bleu nuit à la place du canvas, aucune erreur en console, le tableau des contacts toujours visible sous le canvas. Dans l'onglet Performance des outils de développement, vérifier qu'au repos aucune image n'est rendue.

- [ ] **Step 6: Commit**

```bash
git add assets/js/eclipse/gl.js assets/js/eclipse/main.js projets/eclipse.html assets/style.css
git commit -m "Canvas WebGL2 pilote par un drapeau dirty"
```

---

## Task 16: Les LUT d'atmosphère

**Files:**
- Create: `assets/js/eclipse/atmosphere.glsl.js`, `assets/js/eclipse/luts.js`

- [ ] **Step 1: Écrire `assets/js/eclipse/atmosphere.glsl.js`**

```js
// Fragments GLSL partages entre la construction des LUT et le rendu du ciel.
// Regrouper ces definitions ici garantit que la LUT de transmittance et le
// raymarch utilisent exactement les memes densites: si elles divergeaient,
// le ciel serait faux d'une maniere tres difficile a diagnostiquer.

export const ATMOSPHERE = `
const float R_SOL = 6360000.0;      // rayon de la planete, en metres
const float R_ATMO = 6460000.0;     // sommet de l'atmosphere

const vec3 BETA_RAYLEIGH = vec3(5.802e-6, 13.558e-6, 33.100e-6);
const float H_RAYLEIGH = 8000.0;

const float BETA_MIE = 3.996e-6;
const float BETA_MIE_ABSORPTION = 4.40e-6;
const float H_MIE = 1200.0;
const float G_MIE = 0.80;

// Absorption par l'ozone: profil triangulaire centre sur 25 km, demi-largeur
// 15 km. C'est elle qui donne au crepuscule son bleu profond -- et le sujet
// de cette page est un crepuscule.
const vec3 BETA_OZONE = vec3(0.650e-6, 1.881e-6, 0.085e-6);

vec3 densites(float altitude) {
  float rayleigh = exp(-altitude / H_RAYLEIGH);
  float mie = exp(-altitude / H_MIE);
  float ozone = max(0.0, 1.0 - abs(altitude - 25000.0) / 15000.0);
  return vec3(rayleigh, mie, ozone);
}

vec3 extinction(float altitude) {
  vec3 d = densites(altitude);
  return BETA_RAYLEIGH * d.x
       + (BETA_MIE + BETA_MIE_ABSORPTION) * d.y
       + BETA_OZONE * d.z;
}

float phaseRayleigh(float cosTheta) {
  return 3.0 / (16.0 * 3.14159265) * (1.0 + cosTheta * cosTheta);
}

float phaseMie(float cosTheta) {
  float g = G_MIE;
  float g2 = g * g;
  float d = 1.0 + g2 - 2.0 * g * cosTheta;
  return 3.0 / (8.0 * 3.14159265) * ((1.0 - g2) * (1.0 + cosTheta * cosTheta))
       / ((2.0 + g2) * pow(max(d, 1e-4), 1.5));
}

// Distance du point p a la sortie de la sphere de rayon r, dans la direction
// dir. Rend -1 si le rayon manque la sphere.
float intersectionSphere(vec3 p, vec3 dir, float r) {
  float b = dot(p, dir);
  float c = dot(p, p) - r * r;
  float disc = b * b - c;
  if (disc < 0.0) return -1.0;
  return -b + sqrt(disc);
}
`;
```

- [ ] **Step 2: Écrire `assets/js/eclipse/luts.js`**

```js
// Construction des trois LUT. Elles sont INDEPENDANTES DU LIEU, donc calculees
// une seule fois et partagees par les deux panneaux.

import { createProgram, drawQuad, createTexture, renderToTexture, RGBA16F, RGB32F } from './gl.js';
import { ATMOSPHERE } from './atmosphere.glsl.js';
import { buildFluxLut, LUT_D, LUT_RATIO } from './flux.js';

export const TRANSMITTANCE_L = 256;
export const TRANSMITTANCE_H = 64;
export const MULTISCATTER_N = 32;

const FS_TRANSMITTANCE = `#version 300 es
precision highp float;
out vec4 sortie;
uniform vec2 uTaille;
${ATMOSPHERE}

void main() {
  vec2 uv = gl_FragCoord.xy / uTaille;
  float altitude = uv.y * (R_ATMO - R_SOL);
  float cosZenith = uv.x * 2.0 - 1.0;

  vec3 p = vec3(0.0, R_SOL + altitude, 0.0);
  vec3 dir = vec3(sqrt(max(0.0, 1.0 - cosZenith * cosZenith)), cosZenith, 0.0);

  float distance = intersectionSphere(p, dir, R_ATMO);
  const int PAS = 40;
  vec3 optique = vec3(0.0);
  for (int i = 0; i < PAS; i++) {
    float t = (float(i) + 0.5) / float(PAS) * distance;
    float h = length(p + dir * t) - R_SOL;
    optique += extinction(max(h, 0.0)) * (distance / float(PAS));
  }
  sortie = vec4(exp(-optique), 1.0);
}`;

export function buildLuts(gl) {
  const transmittance = createTexture(gl, TRANSMITTANCE_L, TRANSMITTANCE_H, RGBA16F);
  const programme = createProgram(gl, FS_TRANSMITTANCE, 'transmittance');
  renderToTexture(gl, transmittance, TRANSMITTANCE_L, TRANSMITTANCE_H, () => {
    gl.useProgram(programme);
    gl.uniform2f(gl.getUniformLocation(programme, 'uTaille'),
                 TRANSMITTANCE_L, TRANSMITTANCE_H);
    drawQuad(gl);
  });

  const fluxData = buildFluxLut();
  const flux = createTexture(gl, LUT_D, LUT_RATIO, RGB32F, fluxData);

  return { transmittance, flux, multiscatter: null };
}
```

- [ ] **Step 3: Vérifier visuellement la LUT de transmittance**

Ajouter temporairement dans `main.js`, à la place du `clear` de `dessiner`, un affichage plein cadre de la texture de transmittance. Attendu : un dégradé continu, blanc en haut (altitude élevée, atmosphère traversée mince) virant au rouge sombre puis au noir vers le bas à gauche (visée rasante depuis le sol, forte extinction du bleu). **Si l'image est uniformément noire ou blanche, la LUT est fausse — ne pas continuer.**

Retirer l'affichage temporaire une fois la vérification faite.

- [ ] **Step 4: Commit**

```bash
git add assets/js/eclipse/atmosphere.glsl.js assets/js/eclipse/luts.js
git commit -m "LUT de transmittance et de flux"
```

---

## Task 17: Ciel sans éclipse

Étape de calibrage : on rend un ciel ordinaire et on vérifie qu'il ressemble à un ciel. Introduire l'éclipse avant d'avoir validé ce point rendrait tout diagnostic impossible.

**Files:**
- Create: `assets/js/eclipse/sky.glsl.js`, `assets/js/eclipse/sky.js`
- Modify: `assets/js/eclipse/main.js`

- [ ] **Step 1: Écrire `assets/js/eclipse/sky.glsl.js`**

Shader de diffusion simple, projection équidistante (azimut → x, altitude → y, conformément au §4.4 de la spec), sol analytique, sans aucune notion de Lune pour l'instant.

```js
import { ATMOSPHERE } from './atmosphere.glsl.js';

export const FS_SKY = `#version 300 es
precision highp float;
out vec4 sortie;

uniform vec2 uTaille;          // taille du panneau en pixels
uniform vec2 uOrigine;         // coin bas-gauche du panneau
uniform float uSunAz;          // azimut du Soleil, en radians
uniform float uSunAlt;         // altitude du Soleil, en radians
uniform float uRegardAz;       // decalage du regard, en radians
uniform float uChampH;         // champ horizontal, en radians
uniform vec3 uFlux;            // fraction de flux visible, par canal
uniform sampler2D uTransmittance;
uniform float uExposition;

${ATMOSPHERE}

const vec3 IRRADIANCE_SOLAIRE = vec3(1.0);

vec3 transmittance(float altitude, float cosZenith) {
  vec2 uv = vec2(cosZenith * 0.5 + 0.5, altitude / (R_ATMO - R_SOL));
  return texture(uTransmittance, clamp(uv, 0.0, 1.0)).rgb;
}

// Projection equidistante: l'azimut est lineaire en x, l'altitude en y.
// L'horizon reste donc une droite, contrairement a une rectilinéaire.
vec3 directionDeVisee(vec2 uv, float ratio) {
  float az = uRegardAz + (uv.x - 0.5) * uChampH;
  float alt = (uv.y - 0.5) * uChampH / ratio;
  return vec3(sin(az) * cos(alt), sin(alt), cos(az) * cos(alt));
}

// Courbe filmique a pied doux. Fixe et partagee par les deux panneaux:
// une auto-exposition rendrait la comparaison mensongere.
vec3 tonemap(vec3 x) {
  x *= uExposition;
  const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
  return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main() {
  vec2 uv = (gl_FragCoord.xy - uOrigine) / uTaille;
  float ratio = uTaille.x / uTaille.y;
  vec3 dir = directionDeVisee(uv, ratio);

  vec3 soleil = vec3(sin(uSunAz) * cos(uSunAlt), sin(uSunAlt), cos(uSunAz) * cos(uSunAlt));
  vec3 origine = vec3(0.0, R_SOL + 2.0, 0.0);

  bool versLeSol = dir.y < 0.0;
  vec3 dirCiel = versLeSol ? vec3(dir.x, -dir.y, dir.z) : dir;

  float distance = intersectionSphere(origine, dirCiel, R_ATMO);
  float cosTheta = dot(dirCiel, soleil);

  const int PAS = 32;
  vec3 diffusee = vec3(0.0);
  vec3 transmittanceCumulee = vec3(1.0);

  for (int i = 0; i < PAS; i++) {
    // pas resserres pres de l'observateur, ou la densite est la plus forte
    float t0 = pow(float(i) / float(PAS), 2.0) * distance;
    float t1 = pow(float(i + 1) / float(PAS), 2.0) * distance;
    float dt = t1 - t0;
    vec3 p = origine + dirCiel * (t0 + dt * 0.5);
    float h = max(0.0, length(p) - R_SOL);

    vec3 dens = densites(h);
    vec3 diffusionRayleigh = BETA_RAYLEIGH * dens.x;
    float diffusionMie = BETA_MIE * dens.y;

    float cosZenithSoleil = dot(normalize(p), soleil);
    vec3 versLeSoleil = transmittance(h, cosZenithSoleil);

    vec3 apport = (diffusionRayleigh * phaseRayleigh(cosTheta)
                 + diffusionMie * phaseMie(cosTheta))
                * versLeSoleil * IRRADIANCE_SOLAIRE * uFlux;

    vec3 ext = extinction(h) * dt;
    vec3 pasTransmittance = exp(-ext);
    diffusee += transmittanceCumulee * apport * dt;
    transmittanceCumulee *= pasTransmittance;
  }

  vec3 couleur = diffusee;

  if (versLeSol) {
    // sol lambertien sobre, eclaire par le Soleil direct et par le ciel
    float cosIncidence = max(0.0, soleil.y);
    vec3 direct = transmittance(0.0, cosIncidence) * cosIncidence * uFlux;
    vec3 albedo = vec3(0.10, 0.095, 0.085);
    vec3 sol = albedo * (direct * 0.6 + diffusee * 2.0);
    // perspective aerienne: le sol lointain se noie dans la diffusion
    float melange = clamp(1.0 - abs(dir.y) * 6.0, 0.0, 1.0);
    couleur = mix(sol, diffusee, melange * 0.8);
  }

  sortie = vec4(pow(tonemap(couleur), vec3(1.0 / 2.2)), 1.0);
}`;
```

- [ ] **Step 2: Écrire `assets/js/eclipse/sky.js`**

```js
// Passe ciel: dessine UN panneau. Ce module ignore tout de la frise, des
// selecteurs et du DOM -- il ne recoit qu'un etat et une zone de l'ecran.

import { createProgram, drawQuad } from './gl.js';
import { FS_SKY } from './sky.glsl.js';

const DEG = Math.PI / 180;
export const CHAMP_HORIZONTAL = 120 * DEG;

// Exposition fixe, calibree une fois pour que le plein jour soit correctement
// expose. Ni auto-exposition, ni adaptation temporelle: c'est la condition
// pour que les deux panneaux restent comparables.
export const EXPOSITION = 18.0;

export function createSky(gl) {
  const programme = createProgram(gl, FS_SKY, 'ciel');
  const u = (nom) => gl.getUniformLocation(programme, nom);
  const uniformes = {
    taille: u('uTaille'), origine: u('uOrigine'),
    sunAz: u('uSunAz'), sunAlt: u('uSunAlt'),
    regardAz: u('uRegardAz'), champH: u('uChampH'),
    flux: u('uFlux'), transmittance: u('uTransmittance'),
    exposition: u('uExposition'),
  };

  return function dessinerCiel(etat, zone, luts) {
    gl.useProgram(programme);
    gl.viewport(zone.x, zone.y, zone.w, zone.h);
    gl.enable(gl.SCISSOR_TEST);
    gl.scissor(zone.x, zone.y, zone.w, zone.h);

    gl.uniform2f(uniformes.taille, zone.w, zone.h);
    gl.uniform2f(uniformes.origine, zone.x, zone.y);
    gl.uniform1f(uniformes.sunAz, etat.sunAz * DEG);
    gl.uniform1f(uniformes.sunAlt, etat.sunAlt * DEG);
    gl.uniform1f(uniformes.regardAz, etat.regardAz * DEG);
    gl.uniform1f(uniformes.champH, CHAMP_HORIZONTAL);
    gl.uniform3f(uniformes.flux, etat.fluxR, etat.fluxG, etat.fluxB);
    gl.uniform1f(uniformes.exposition, EXPOSITION);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, luts.transmittance);
    gl.uniform1i(uniformes.transmittance, 0);

    drawQuad(gl);
    gl.disable(gl.SCISSOR_TEST);
  };
}
```

- [ ] **Step 3: Câbler dans `main.js`**

Remplacer la fonction `dessiner` par un rendu d'un seul panneau plein cadre, et importer `buildLuts` et `createSky`. Utiliser `stateAt(etat.gauche, etat.tSecondes)` et forcer `fluxR = fluxG = fluxB = 1` pour cette tâche.

- [ ] **Step 4: Vérifier le ciel ordinaire**

Attendu, avec le flux forcé à 1 : un ciel bleu franc au zénith, dégradé vers un horizon plus pâle, le sol sombre dans la moitié basse. En faisant varier `uSunAlt` à la main jusqu'à des valeurs proches de zéro, on doit obtenir des teintes de coucher de soleil orangées près de l'horizon.

**Point de contrôle décisif.** Si le ciel n'est pas bleu, ou si l'horizon ne se réchauffe pas quand le Soleil descend, le modèle de diffusion est faux. Le corriger ici, avant toute introduction de l'éclipse. Les suspects, dans l'ordre : l'échantillonnage de la LUT de transmittance (`cosZenith` mal remis à l'échelle), le signe de `dir.y`, et la valeur de `EXPOSITION`.

- [ ] **Step 5: Commit**

```bash
git add assets/js/eclipse/sky.glsl.js assets/js/eclipse/sky.js assets/js/eclipse/main.js
git commit -m "Ciel diffusant sans eclipse, calibre sur un ciel ordinaire"
```

---

## Task 18: L'ombre lunaire le long du rayon

Le cœur de la spec, §4.2. C'est ce qui fait la différence entre une simple atténuation et une vraie éclipse.

**Files:**
- Modify: `assets/js/eclipse/sky.glsl.js`, `assets/js/eclipse/sky.js`, `assets/js/eclipse/luts.js`

- [ ] **Step 1: Ajouter la fonction de fraction de flux au shader**

Dans `sky.glsl.js`, ajouter avant `main()`, et déclarer les uniformes `uMoonDir`, `uRSun`, `uRMoon`, `uDMoonKm`, `uDSunKm`, `uFluxLut` :

```glsl
// Fraction de flux solaire visible DEPUIS UN POINT DONNE de l'atmosphere.
//
// Un deplacement delta du point d'echantillonnage par rapport a l'observateur
// decale la direction apparente de la Lune de -delta_perp / D_lune, et celle
// du Soleil de -delta_perp / D_soleil. Comme la Lune est 400 fois plus proche,
// c'est elle qui domine: le cone d'ombre, sa largeur d'une centaine de
// kilometres et son inclinaison tombent de cette seule expression.
vec3 fluxAuPoint(vec3 delta) {
  vec3 perp = delta - dot(delta, uSunDir) * uSunDir;
  float k = 1.0 / (uDMoonKm * 1000.0) - 1.0 / (uDSunKm * 1000.0);
  vec3 separationVec = (uMoonDir - uSunDir) + perp * k;
  float d = length(separationVec);

  float u = clamp(d / uRSun / 2.2, 0.0, 1.0);
  float v = clamp((uRMoon / uRSun - 0.90) / 0.20, 0.0, 1.0);
  return texture(uFluxLut, vec2(u, v)).rgb;
}
```

Note : `uRSun` et `uRMoon` sont en radians, et `d` est une longueur de corde entre deux vecteurs unitaires — pour des angles de l'ordre du degré, corde et angle coïncident à mieux que 10⁻⁵ près, ce qui est très en dessous de la résolution de la LUT.

- [ ] **Step 2: Utiliser la fraction locale dans le raymarch**

Dans la boucle de `main()`, remplacer le facteur `uFlux` de la ligne `apport` par la fraction évaluée localement :

```glsl
    vec3 delta = p - origine;
    vec3 fluxLocal = fluxAuPoint(delta);

    vec3 apport = (diffusionRayleigh * phaseRayleigh(cosTheta)
                 + diffusionMie * phaseMie(cosTheta))
                * versLeSoleil * IRRADIANCE_SOLAIRE * fluxLocal;
```

Pour le sol, conserver `uFlux` : le sol est au niveau de l'observateur, donc la fraction locale y est bien celle de l'observateur.

- [ ] **Step 3: Passer la LUT de flux et les nouveaux uniformes depuis `sky.js`**

Ajouter les emplacements d'uniformes correspondants et les renseigner depuis l'état interpolé (`rSun`, `rMoon`, `dSunKm`, `dMoonKm`), en construisant `uMoonDir` à partir de `moonAz` et `moonAlt` comme `uSunDir` l'est déjà à partir de `sunAz` et `sunAlt`. Lier la texture `luts.flux` sur l'unité 1.

- [ ] **Step 4: Vérifier l'anneau de crépuscule**

Sélectionner Reykjavík (le Soleil y est assez haut pour que l'anneau soit lisible, cf. spec §7) et amener la frise à la totalité.

Attendu : le ciel s'assombrit fortement autour du Soleil, **et** une bande claire subsiste près de l'horizon tout autour — c'est l'anneau à 360°. En balayant le regard à l'opposé du Soleil, l'horizon doit rester nettement plus clair que le zénith.

**Si le ciel s'assombrit uniformément, sans anneau, la fonction `fluxAuPoint` ne varie pas avec `delta`.** Vérifier alors le signe et l'échelle de `k` : `uDMoonKm` est en kilomètres et `delta` en mètres, d'où la multiplication par 1000.

- [ ] **Step 5: Commit**

```bash
git add assets/js/eclipse/sky.glsl.js assets/js/eclipse/sky.js assets/js/eclipse/luts.js
git commit -m "Ombre lunaire evaluee le long du rayon: anneau de crepuscule a 360 degres"
```

---

## Task 19: Diffusion multiple

**Files:**
- Modify: `assets/js/eclipse/luts.js`, `assets/js/eclipse/sky.glsl.js`

- [ ] **Step 1: Ajouter la LUT de diffusion multiple**

Dans `luts.js`, ajouter un shader `FS_MULTISCATTER` de `MULTISCATTER_N × MULTISCATTER_N`, paramétré par (cosinus de l'angle zénithal solaire en x, altitude en y). Pour chaque texel, échantillonner uniformément une sphère de directions (64 directions suffisent), accumuler la lumière diffusée une fois, et rendre la série géométrique `L / (1 - f)` qui approche les ordres supérieurs — c'est la formulation de Hillaire (2020).

Rendre la texture dans `buildLuts` et l'ajouter à l'objet retourné sous la clé `multiscatter`.

- [ ] **Step 2: Ajouter le terme dans le raymarch**

Dans `sky.glsl.js`, déclarer `uniform sampler2D uMultiscatter;` et ajouter dans la boucle, après `apport` :

```glsl
    vec2 msUv = vec2(cosZenithSoleil * 0.5 + 0.5, h / (R_ATMO - R_SOL));
    vec3 multiple = texture(uMultiscatter, clamp(msUv, 0.0, 1.0)).rgb
                  * (diffusionRayleigh + diffusionMie) * fluxVoisinage;
    apport += multiple;
```

- [ ] **Step 3: Ajouter la moyenne de voisinage**

Conformément au §4.3 de la spec, la diffusion multiple qui éclaire un point sous l'ombre provient d'une région d'une centaine de kilomètres. Ajouter dans `sky.glsl.js` :

```glsl
// Moyenne de la fraction de flux sur un voisinage de +/- 50 km: la lumiere
// diffusee plusieurs fois qui atteint un point sous l'ombre vient d'une
// region de cet ordre. Approximation assumee, declaree dans la page.
vec3 fluxVoisin(vec3 delta) {
  const float RAYON = 50000.0;
  vec3 e1 = normalize(cross(uSunDir, vec3(0.0, 1.0, 0.0)));
  vec3 e2 = cross(uSunDir, e1);
  return 0.25 * (fluxAuPoint(delta + e1 * RAYON) + fluxAuPoint(delta - e1 * RAYON)
               + fluxAuPoint(delta + e2 * RAYON) + fluxAuPoint(delta - e2 * RAYON));
}
```

et l'utiliser pour `fluxVoisinage` dans le terme de diffusion multiple.

- [ ] **Step 4: Vérifier**

Attendu : le ciel gagne en profondeur, l'horizon devient plus lumineux et moins saturé, et surtout la scène de totalité n'est plus quasi noire mais bleu nuit avec un anneau chaud à l'horizon. Comparer avant/après en commentant le terme : la différence doit être nette.

- [ ] **Step 5: Commit**

```bash
git add assets/js/eclipse/luts.js assets/js/eclipse/sky.glsl.js
git commit -m "Diffusion multiple approchee, moyennee sur le voisinage sous l'ombre"
```

---

## Task 20: Deux panneaux, sélecteurs et frise

**Files:**
- Create: `assets/js/eclipse/ui.js`
- Modify: `assets/js/eclipse/main.js`, `projets/eclipse.html`, `en/projects/eclipse.html`, `assets/style.css`

- [ ] **Step 1: Ajouter les contrôles dans le HTML**

Dans les deux pages, à l'intérieur de `#eclipse-sim`, après le canvas :

```html
    <div class="sim-controls">
      <div class="sim-sites">
        <label>Lieu de gauche
          <select data-panneau="gauche">
            <option value="paris" selected>Paris</option>
            <option value="espagne">Espagne</option>
            <option value="reykjavik">Reykjavík</option>
          </select>
        </label>
        <label>Lieu de droite
          <select data-panneau="droite">
            <option value="paris">Paris</option>
            <option value="espagne" selected>Espagne</option>
            <option value="reykjavik">Reykjavík</option>
          </select>
        </label>
      </div>
      <div class="sim-time">
        <button type="button" data-action="lecture" aria-pressed="false">Lecture</button>
        <label class="sr-only" for="sim-frise">Instant de l'éclipse</label>
        <input type="range" id="sim-frise" min="0" max="1000" value="0" step="1">
      </div>
      <div class="sim-readout">
        <output data-panneau="gauche" aria-live="polite"></output>
        <output data-panneau="droite" aria-live="polite"></output>
      </div>
    </div>
```

Traduire les libellés dans la version anglaise.

- [ ] **Step 2: Écrire `assets/js/eclipse/ui.js`**

Le module câble les contrôles et rend un objet observable. Il ne connaît que `data.js`.

Responsabilités : lire et écrire `tSecondes` depuis la frise (la frise est graduée de 0 à 1000 et convertie vers la fenêtre du site le plus long) ; basculer la lecture ; gérer le glissement horizontal et les flèches gauche/droite pour `regardAz` ; mettre à jour les deux `<output>`, **au plus une fois par seconde**, avec l'heure locale, l'altitude solaire, la magnitude et l'obscuration ; appeler un `onChange` fourni qui positionne `etat.sale = true`.

L'heure locale se formate avec `Intl.DateTimeFormat` en passant `timeZone: site.tz`, sans dépendance.

- [ ] **Step 3: Dessiner les deux panneaux**

Dans `main.js`, découper le cadre en deux zones. Sous 48 rem, empiler verticalement plutôt qu'horizontalement :

```js
function zones(gl) {
  const l = gl.drawingBufferWidth;
  const h = gl.drawingBufferHeight;
  if (l < h * 1.2) {
    const demi = Math.floor(h / 2);
    return [{ x: 0, y: demi, w: l, h: h - demi }, { x: 0, y: 0, w: l, h: demi }];
  }
  const demi = Math.floor(l / 2);
  return [{ x: 0, y: 0, w: demi, h }, { x: demi, y: 0, w: l - demi, h }];
}
```

Appeler `dessinerCiel` une fois par zone, avec l'état du site correspondant et le **même** `regardAz` : le décalage du regard est relatif à la direction du Soleil de chaque lieu, ce qui garde les deux vues comparables.

- [ ] **Step 4: Styler les contrôles**

Ajouter dans `assets/style.css` les styles de `.sim-controls`, `.sim-sites`, `.sim-time`, `.sim-readout`, en `var(--mono)` et à la taille `0.8125rem`, avec des `<select>` et `<input type="range">` natifs simplement mis à la charte. Ajouter aussi la classe utilitaire `.sr-only` si elle n'existe pas encore dans la feuille.

- [ ] **Step 5: Vérifier**

Attendu : deux ciels côte à côte, une frise commune, Paris à gauche encore lumineux quand l'Espagne à droite est dans la totalité. C'est la démonstration centrale de la page — si elle ne saute pas aux yeux, revoir `EXPOSITION`.

Vérifier aussi : la navigation au clavier atteint les deux `<select>`, le bouton et la frise ; les flèches font tourner le regard quand le canvas a le focus ; les deux `<output>` s'énoncent.

- [ ] **Step 6: Commit**

```bash
git add assets/js/eclipse/ui.js assets/js/eclipse/main.js projets/eclipse.html en/projects/eclipse.html assets/style.css
git commit -m "Deux panneaux comparables, frise commune et controles accessibles"
```

---

## Task 21: Étoiles et planètes

**Files:**
- Modify: `assets/js/eclipse/sky.glsl.js`, `assets/js/eclipse/sky.js`

- [ ] **Step 1: Passer les astres au shader**

Depuis `sky_at_max`, construire un `Float32Array` de triplets (azimut, altitude, magnitude), plafonné à 60 astres, et le transmettre en `uniform vec3 uAstres[60]` avec `uniform int uNbAstres`.

- [ ] **Step 2: Dessiner les astres**

Dans `main()`, après le calcul de `couleur`, ajouter les astres avant le tonemap. L'intensité de chaque astre suit `pow(10.0, -0.4 * magnitude)` mise à l'échelle, et l'ensemble est atténué par un facteur qui ne devient non nul que lorsque la luminance du ciel s'effondre — de sorte que les étoiles n'apparaissent que pendant la totalité, comme dans la réalité.

Dessiner chaque astre comme un point gaussien de quelques pixels dans l'espace de la projection, en tenant compte du repliement de l'azimut à 360°.

- [ ] **Step 3: Vérifier**

Attendu : aucune étoile visible en plein jour ; pendant la totalité en Espagne et à Reykjavík, quelques dizaines de points apparaissent, les plus brillants d'abord, et disparaissent au troisième contact. À Paris, aucune étoile à aucun moment — c'est correct, et c'est un point de plus pour la comparaison.

- [ ] **Step 4: Commit**

```bash
git add assets/js/eclipse/sky.glsl.js assets/js/eclipse/sky.js
git commit -m "Etoiles et planetes apparaissant pendant la totalite"
```

---

## Task 22: L'encart téléobjectif

**Files:**
- Create: `assets/js/eclipse/inset.glsl.js`, `assets/js/eclipse/inset.js`
- Modify: `assets/js/eclipse/main.js`

- [ ] **Step 1: Écrire `assets/js/eclipse/inset.glsl.js`**

Champ d'environ 1,5°, centré sur le Soleil. Contenu :

- le disque solaire, avec le **même** assombrissement centre-bord que `flux.js` (loi quadratique, `SRGB_LIMB_COEFFS` passés en uniformes) ;
- le disque lunaire, opaque, à sa taille angulaire réelle et à sa position réelle relativement au Soleil, déduites de `rSun`, `rMoon` et de la séparation ;
- la couronne, selon le profil de van de Hulst / Baumbach de la spec §4.6 :

```glsl
// Profil radial empirique K+F de van de Hulst / Baumbach. r en rayons solaires.
// Ce n'est PAS une observation: la page le declare explicitement.
float couronne(float r) {
  if (r < 1.0) return 0.0;
  return 1e-6 * (0.0532 * pow(r, -2.5) + 1.425 * pow(r, -7.0) + 2.565 * pow(r, -17.0));
}
```

modulée par des streamers procéduraux (bruit à quelques octaves en coordonnées polaires, allongé radialement), et dont l'intensité globale suit l'effondrement de `uFlux` — la couronne n'apparaît donc qu'au bon moment ;

- l'anneau de diamant aux abords de C2 et C3 : quand la séparation approche `|rSun - rMoon|`, un point brillant au bord du disque lunaire, dont la position suit l'angle du dernier point de contact.

Appliquer le **même** tonemap et la **même** exposition que `sky.glsl.js` — sinon l'encart et le ciel raconteraient deux histoires différentes.

- [ ] **Step 2: Écrire `assets/js/eclipse/inset.js`**

Même forme que `sky.js` : `createInset(gl)` rend une fonction `dessinerEncart(etat, zone)`.

- [ ] **Step 3: Placer les encarts**

Dans `main.js`, après chaque panneau de ciel, dessiner l'encart dans un carré situé en bas à droite de la zone, occupant environ 30 % de sa plus petite dimension, avec une marge. Sur la disposition empilée, garder la même règle relativement à chaque zone.

Encadrer chaque encart d'un liseré d'un pixel en dessinant d'abord un `gl.scissor` légèrement plus grand rempli d'une couleur de trait.

- [ ] **Step 4: Vérifier la géométrie**

Point de contrôle : à Paris au maximum, le disque lunaire doit mordre le disque solaire **sans le couvrir entièrement** ; en Espagne au maximum, il doit le couvrir intégralement et la couronne doit apparaître. La magnitude affichée dans le `<output>` doit être cohérente avec ce qu'on voit dans l'encart.

C'est la vérification la plus directe que la géométrie est juste : si l'encart et les chiffres se contredisent, l'un des deux est faux.

- [ ] **Step 5: Commit**

```bash
git add assets/js/eclipse/inset.glsl.js assets/js/eclipse/inset.js assets/js/eclipse/main.js
git commit -m "Encart teleobjectif: disques, couronne et anneau de diamant"
```

---

## Task 23: Poster de repli et images de partage

**Files:**
- Modify: `assets/js/eclipse/main.js`, `projets/eclipse.html`, `en/projects/eclipse.html`
- Create: `assets/img/eclipse-poster.webp`, `assets/og/eclipse.jpg`, `assets/og/eclipse-en.jpg`

- [ ] **Step 1: Ajouter la route `?poster=1`**

Dans `main.js`, si `new URLSearchParams(location.search).get('poster') === '1'` : forcer le couple Paris | Espagne, positionner la frise à l'instant du maximum en Espagne, rendre à pleine résolution (échelle 1 au lieu de 0,7), puis appeler `canvas.toBlob` et déclencher un téléchargement.

- [ ] **Step 2: Produire le poster**

Ouvrir `http://127.0.0.1:8000/projets/eclipse.html?poster=1`, récupérer le PNG, puis :

```bash
cwebp -q 82 poster.png -o assets/img/eclipse-poster.webp
```

Vérifier que le fichier pèse moins de 200 Ko.

- [ ] **Step 3: Insérer le poster dans les deux pages**

Dans `.sim-fallback`, avant le tableau des contacts :

```html
      <img class="sim-poster" src="/assets/img/eclipse-poster.webp"
           width="1600" height="667" loading="lazy" decoding="async"
           alt="Le ciel au maximum de l'éclipse, vu depuis Paris à gauche et depuis l'Espagne à droite : Paris reste en plein jour tandis que le ciel espagnol est plongé dans la pénombre, un anneau de crépuscule cerclant l'horizon.">
```

Le texte alternatif doit décrire ce que la comparaison montre, pas seulement nommer l'image — c'est le seul accès à cette information pour qui ne voit pas la page.

- [ ] **Step 4: Produire les images de partage**

Créer `assets/og/eclipse.jpg` et `assets/og/eclipse-en.jpg` en 1200 × 630, dans le même esprit que les images `og` existantes, à partir d'un recadrage du poster. Vérifier que les `<meta property="og:image">` des deux pages pointent bien vers elles.

- [ ] **Step 5: Commit**

```bash
git add assets/js/eclipse/main.js assets/img/eclipse-poster.webp assets/og/eclipse.jpg assets/og/eclipse-en.jpg projets/eclipse.html en/projects/eclipse.html
git commit -m "Poster de repli et images de partage"
```

---

## Task 24: Vérification finale — performance, accessibilité, dégradation

**Files:**
- Modify: `assets/js/eclipse/main.js`, `projets/eclipse.html`, `en/projects/eclipse.html`

- [ ] **Step 1: Ajouter la surcouche `?debug=1`**

Afficher, dans un `<div>` en position absolue, les images par seconde, le nombre d'appels de dessin de la dernière image, la taille du tampon de rendu, et les valeurs courantes des deux panneaux.

- [ ] **Step 2: Vérifier le repos**

Charger la page, ne toucher à rien, ouvrir l'onglet Performance et enregistrer cinq secondes.

Attendu : **aucune image rendue**. Si le profil montre des appels continus, le drapeau `dirty` est contourné quelque part — le corriger, c'est l'engagement principal de la spec §5.

- [ ] **Step 3: Vérifier hors écran et onglet caché**

Faire défiler jusqu'à ce que le canvas sorte du cadre pendant la lecture : le rendu doit cesser. Passer à un autre onglet : idem.

- [ ] **Step 4: Vérifier le mouvement réduit**

Activer `prefers-reduced-motion` dans les outils de développement, recharger. Attendu : aucune lecture automatique au chargement, la frise reste pilotable, et chaque déplacement rend exactement une image.

- [ ] **Step 5: Vérifier la dégradation**

Trois vérifications distinctes, toutes obligatoires :

- JavaScript désactivé : le poster et le tableau des contacts s'affichent, la page se lit entièrement.
- WebGL2 désactivé (`webgl2.force_disable` dans Firefox, ou un navigateur sans support) : idem, sans erreur visible.
- Réseau coupé après le premier chargement : la page ne doit dépendre d'aucune ressource tierce.

- [ ] **Step 6: Vérifier l'accessibilité**

Parcours clavier complet, de l'en-tête au pied de page, sans piège de focus. Vérifier que les deux `<output>` sont annoncés, que le canvas porte un `aria-label` à jour, et que les contrastes des contrôles passent en thème clair comme en thème sombre.

- [ ] **Step 7: Mesurer le budget**

```bash
gzip -c assets/data/eclipse-2026-08-12.json | wc -c
cat assets/js/eclipse/*.js | gzip -c | wc -c
```

Attendu : le total doit rester dans l'ordre de grandeur annoncé au §5 de la spec. S'il le dépasse largement, en prendre acte et corriger la spec plutôt que de laisser une affirmation fausse.

- [ ] **Step 8: Lancer toute la suite de tests**

```bash
source .venv/bin/activate && python3 -m pytest tools/eclipse/tests/ -q && node --test tools/js-tests/
```

Attendu : tout passe, dans les deux langages.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "Verification finale: repos, degradation, accessibilite, budget"
```

---

## Auto-relecture du plan

**Couverture de la spec.** Chaque section a sa tâche : §3.1 → tâches 2 à 8 ; §3.2 → tâche 8 ; §3.3 → tâches 13 à 22 ; §4.1 → tâche 3 (avec le test qui encode la correction de physique) ; §4.2 → tâche 18 ; §4.3 → tâches 16 et 19 ; §4.4 → tâches 17 et 20 ; §4.5 → tâche 17 (`EXPOSITION`, partagée) ; §4.6 → tâche 22 ; §5 → tâches 15 et 24 ; §6 → tâche 10 ; §7 → tâche 6 ; §8 → tâches 10, 20 et 24 ; §9 → tâches 10 à 12 et 23 ; §10 → tâches 9 et 24 ; §11 → l'ordre des tâches lui-même.

**Points laissés ouverts, et pourquoi.** Trois valeurs ne sont pas écrites dans ce plan parce qu'elles doivent venir d'une source et non de moi : les coefficients d'assombrissement centre-bord (tâche 3, étape 1), les valeurs publiées NASA (tâche 6) et les coordonnées de la ville espagnole (tâche 6, étape 2). Chacune est accompagnée du critère qui permet de vérifier qu'elle a été correctement relevée. Les inventer serait précisément l'inverse de ce que la page prétend faire.

**Cohérence des noms.** `visible_flux_fraction` / `visibleFluxFraction`, `SRGB_LIMB_COEFFS` dans les deux langages, `stateAt`, `buildFluxLut`, `buildLuts`, `createSky`, `createInset`, `fluxAuPoint`, `fluxVoisin`, `dessinerCiel`, `dessinerEncart` — les mêmes noms sont employés d'une tâche à l'autre. Le tableau `frames` compte treize champs à la tâche 8 comme à la tâche 13.

**Vérifications inter-tâches.** Trois tests existent uniquement pour attraper une divergence entre deux endroits du code, là où une erreur passerait autrement inaperçue : `test_disque_uniforme_redonne_exactement_l_obscuration_geometrique` valide l'intégrale de flux contre la géométrie pure ; `flux.test.js` valide le miroir JavaScript contre Python ; `test_le_flux_reste_sous_l_obscuration_geometrique` valide la physique du §4.1 sur les données réellement produites. Aucun des trois ne doit être assoupli en cas d'échec.
