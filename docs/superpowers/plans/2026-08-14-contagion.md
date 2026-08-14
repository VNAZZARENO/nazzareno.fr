# La contagion, ou moins qu'on ne dit — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La page projet « La contagion, ou moins qu'on ne dit » (FR + EN) : le biais de
Forbes-Rigobon recalculé sur S&P 500 × CAC 40, démontré par simulation, corrigé, avec quatre
figures SVG calculées et un explorateur interactif.

**Architecture:** Trois étages comme la page éclipse : calcul hors ligne
(`tools/contagion/`, numpy pur, données Yahoo Finance gelées dans le dépôt via yfinance) → artefacts versionnés
(`assets/data/contagion.json`, SVG injectés entre repères dans les deux pages HTML) →
navigateur (deux modules ES sans dépendance, parité testée sous node).

**Tech Stack:** Python 3.12 (`.venv`, numpy ; matplotlib pour les seules images OG), pytest,
node --test, HTML/CSS/JS du site (aucun bundler, aucune dépendance externe).

**Spec:** `docs/superpowers/specs/2026-08-14-contagion-design.md`

**Écarts à la spec, assumés ici :** (1) pas de dépendance pandas en propre — yfinance
l'apporte et `data.py` consomme son DataFrame, mais tout le reste (returns, deciles,
rolling, export, figures) est numpy + stdlib ; (2) le JSON exporté ne porte pas
le vecteur de dates (spec §4.3) — l'explorateur n'en a pas besoin, seules les bornes de la
période vont dans `meta`, ce qui tient le budget de taille.

**Révision du 14 août 2026 :** la tâche 1 visait Stooq ; la sonde a montré `^spx` disparu
(remplacé par un CFD limité à 2013) et un mur anti-robot. Sur décision de Vincent, la
source est Yahoo Finance via yfinance (`^GSPC`, `^FCHI`), la doctrine de gel inchangée.
La tâche 1 ci-dessous est la version révisée.

**Conventions transverses, valables pour toutes les tâches :**

- Tout se lance depuis la racine du dépôt : `source .venv/bin/activate && python3 …`.
- Tests Python : `python3 -m pytest tools/contagion/tests -q`. Tests node :
  `node --test tools/js-tests/`.
- Style des commits : français sans accents, corps qui explique le pourquoi, signature
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Prose des pages : pas de tiret cadratin, espace insécable avant % et pt (même convention
  que `tools/eclipse/figures.py`), aucun nombre saisi à la main — les valeurs notées `⟨…⟩`
  dans ce plan sont remplacées par les valeurs calculées au moment de la rédaction, puis
  verrouillées par les tests de la tâche 14.
- Conventions numériques, identiques partout (Python ET JS) : corrélation de Pearson et
  variances avec diviseur n (population), pas n−1 ; seuil de quantile q sur `|rx|` : trier
  les `|rx|` croissants, `seuil = tri[floor(q·n)]`, garder les paires où `|rx| ≥ seuil`.

---

### Task 1: Données Yahoo Finance — sonde, gel, manifeste (version révisée)

Le seul risque externe du projet, donc la première tâche. On vérifie que yfinance sert
bien `^GSPC` et `^FCHI` en profondeur suffisante, on gèle les CSV dans le dépôt, on écrit
le manifeste.

**Files:**
- Create: `tools/contagion/__init__.py` (vide)
- Create: `tools/contagion/requirements.txt`
- Create: `tools/contagion/data.py`
- Create: `tools/contagion/data/` (CSV gelés + `manifeste.json`)
- Create: `tools/contagion/tests/__init__.py` (vide)
- Test: `tools/contagion/tests/test_data.py`

- [ ] **Step 1: Installer et sonder**

```bash
source .venv/bin/activate && pip install yfinance numpy matplotlib
python3 - <<'EOF'
import yfinance
for s in ("^GSPC", "^FCHI"):
    h = yfinance.Ticker(s).history(period="max", auto_adjust=False)
    print(s, len(h), h.index[0].date(), "->", h.index[-1].date())
EOF
```

Attendu : plusieurs milliers de lignes chacun, `^GSPC` depuis les années 1920,
`^FCHI` depuis ~1990. Si l'un des deux manque ou s'arrête avant 25 ans d'historique,
**s'arrêter et faire valider un changement de source** (spec §4.1) avant de continuer.

- [ ] **Step 2: Écrire le test (échoue faute de données gelées)**

```python
# tools/contagion/tests/test_data.py
"""Le jeu gele est present, integre, et assez profond pour la page."""
import csv
import datetime
import hashlib
import json
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[3]
DOSSIER = RACINE / "tools" / "contagion" / "data"


def lire(nom):
    with open(DOSSIER / nom, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_manifeste_et_sommes():
    manifeste = json.loads((DOSSIER / "manifeste.json").read_text())
    assert set(manifeste["fichiers"]) == {"spx.csv", "cac.csv"}
    for nom, attendu in manifeste["fichiers"].items():
        sha = hashlib.sha256((DOSSIER / nom).read_bytes()).hexdigest()
        assert sha == attendu["sha256"], nom
        assert attendu["symbole"] in ("^GSPC", "^FCHI")
        assert attendu["source"].startswith("Yahoo Finance via yfinance")
    assert "telecharge_utc" in manifeste


def test_profondeur_et_ordre():
    for nom in ("spx.csv", "cac.csv"):
        lignes = lire(nom)
        dates = [datetime.date.fromisoformat(l["Date"]) for l in lignes]
        assert dates == sorted(dates), f"{nom}: dates non croissantes"
        assert len(set(dates)) == len(dates), f"{nom}: doublons"
        assert (dates[-1] - dates[0]).days > 25 * 365, f"{nom}: historique court"
        for l in lignes:
            assert float(l["Close"]) > 0.0
```

- [ ] **Step 3: Vérifier que le test échoue**

Run: `source .venv/bin/activate && python3 -m pytest tools/contagion/tests/test_data.py -q`
Expected: FAIL (dossier `data/` absent).

- [ ] **Step 4: Écrire `data.py` et `requirements.txt`, installer numpy**

```
# tools/contagion/requirements.txt
numpy
matplotlib
yfinance
```

```python
# tools/contagion/data.py
"""Telecharge les clotures Yahoo Finance une fois et les gele dans le depot.

Usage: source .venv/bin/activate && python3 -m tools.contagion.data

A ne relancer que pour geler un nouveau jeu: la page est datee, pas vivante.
Le manifeste enregistre symbole, source, horodatage et sommes SHA-256, pour
que le calcul soit rejouable sur exactement les memes octets. Le CSV est
reecrit par nos soins (Date,Open,High,Low,Close,Volume): le gel porte sur des
octets que NOUS avons produits, pas sur un format tiers susceptible de bouger.
"""
import datetime
import hashlib
import json
import math
import pathlib

import yfinance

RACINE = pathlib.Path(__file__).resolve().parents[2]
DOSSIER = RACINE / "tools" / "contagion" / "data"

SYMBOLES = {"spx.csv": "^GSPC", "cac.csv": "^FCHI"}


def _case(valeur):
    return "" if valeur is None or (isinstance(valeur, float) and math.isnan(valeur)) \
        else f"{valeur:.6f}"


def main():
    DOSSIER.mkdir(exist_ok=True)
    manifeste = {"telecharge_utc":
                 datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                 "fichiers": {}}
    for nom, symbole in SYMBOLES.items():
        histo = yfinance.Ticker(symbole).history(period="max", auto_adjust=False)
        histo = histo.dropna(subset=["Close"])
        if len(histo) < 5000:
            raise SystemExit(f"{symbole}: {len(histo)} lignes seulement")
        lignes = ["Date,Open,High,Low,Close,Volume"]
        for ts, l in histo.iterrows():
            lignes.append(",".join([ts.date().isoformat(), _case(l["Open"]),
                                    _case(l["High"]), _case(l["Low"]),
                                    _case(l["Close"]), str(int(l["Volume"] or 0))]))
        octets = ("\n".join(lignes) + "\n").encode("utf-8")
        (DOSSIER / nom).write_bytes(octets)
        manifeste["fichiers"][nom] = {
            "symbole": symbole,
            "source": f"Yahoo Finance via yfinance {yfinance.__version__}",
            "sha256": hashlib.sha256(octets).hexdigest(), "octets": len(octets)}
        print(nom, len(octets), "octets")
    (DOSSIER / "manifeste.json").write_text(
        json.dumps(manifeste, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
```

Run: `source .venv/bin/activate && pip install -r tools/contagion/requirements.txt && python3 -m tools.contagion.data`

- [ ] **Step 5: Vérifier que le test passe**

Run: `python3 -m pytest tools/contagion/tests/test_data.py -q`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add tools/contagion/
git commit  # "Donnees Yahoo Finance gelees pour la page contagion, avec manifeste"
```

---

### Task 2: `bias.py` — la formule et son inversion

Fonctions pures, cœur mathématique de toute la page.

**Files:**
- Create: `tools/contagion/bias.py`
- Test: `tools/contagion/tests/test_bias.py`

- [ ] **Step 1: Écrire les tests (échouent)**

```python
# tools/contagion/tests/test_bias.py
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
    assert valeurs == sorted(valeurs)


def test_impaire_en_rho():
    assert rho_conditionnelle(-0.4, 2.0) == pytest.approx(-rho_conditionnelle(0.4, 2.0))


def test_delta_relatif():
    assert delta_relatif(2.0, 1.0) == pytest.approx(1.0)
    assert delta_relatif(0.5, 1.0) == pytest.approx(-0.5)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_bias.py -q`
Expected: FAIL, `ModuleNotFoundError: tools.contagion.bias`.

- [ ] **Step 3: Implémenter**

```python
# tools/contagion/bias.py
"""La formule de Forbes et Rigobon (2002), et son inversion.

Modele y = a + b*x + e, e independant de x et homoscedastique. Conditionner
sur un evenement defini sur x seul ne change pas b, seulement le rapport
signal sur bruit: la correlation d'echantillon monte avec la variance de x
sans qu'aucun parametre structurel n'ait bouge. C'est tout le sujet de la
page; ces trois fonctions sont les seules formules du projet.
"""
import math


def delta_relatif(var_sous_echantillon, var_pleine):
    """L'exces relatif de variance du sous-echantillon, le delta de la formule."""
    return var_sous_echantillon / var_pleine - 1.0


def rho_conditionnelle(rho, delta):
    """Correlation d'echantillon attendue sous conditionnement, a rho vrai constant."""
    return rho * math.sqrt(1.0 + delta) / math.sqrt(1.0 + delta * rho * rho)


def correction(rho_cond, delta):
    """L'inversion: retrouve la correlation non conditionnelle. C'est la correction F-R."""
    return rho_cond / math.sqrt(1.0 + delta * (1.0 - rho_cond * rho_cond))
```

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_bias.py -q`
Expected: PASS (34 tests, paramétrés compris).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/bias.py tools/contagion/tests/test_bias.py
git commit  # "La formule de Forbes-Rigobon et son inversion, testees sur leurs proprietes"
```

---

### Task 3: `returns.py` — rendements, moyenne mobile 2 jours, appariement

**Files:**
- Create: `tools/contagion/returns.py`
- Test: `tools/contagion/tests/test_returns.py`

- [ ] **Step 1: Écrire les tests (échouent)**

```python
# tools/contagion/tests/test_returns.py
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
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_returns.py -q`
Expected: FAIL, module absent.

- [ ] **Step 3: Implémenter**

```python
# tools/contagion/returns.py
"""Des CSV geles aux paires de rendements comparables.

Paris ferme a 17 h 30, New York a 22 h: les rendements du meme jour calendaire
ne se recouvrent que partiellement. On suit Forbes et Rigobon eux-memes:
rendements logarithmiques en moyenne mobile 2 jours, calcules sur le calendrier
propre de chaque marche, puis apparies sur l'intersection des dates. Le prix de
ce choix, une autocorrelation MA(1), est declare dans la page et verifie par
test plutot que passe sous silence.
"""
import csv
import pathlib

import numpy as np

DOSSIER = pathlib.Path(__file__).resolve().parent / "data"


def _lire_csv(nom):
    with open(DOSSIER / nom, newline="", encoding="utf-8") as f:
        lignes = [l for l in csv.DictReader(f) if l.get("Close")]
    return [l["Date"] for l in lignes], np.array([float(l["Close"]) for l in lignes])


def rendements_log(dates, clotures):
    r = np.diff(np.log(np.asarray(clotures)))
    return list(dates[1:]), r


def paires(dates, rendements):
    """Moyenne mobile 2 jours sur le calendrier propre: (r_t + r_{t-1}) / 2."""
    r2 = (rendements[1:] + rendements[:-1]) / 2.0
    return list(dates[1:]), r2


def serie_appariee(dates_a, r_a, dates_b, r_b):
    communes = sorted(set(dates_a) & set(dates_b))
    ia = {d: i for i, d in enumerate(dates_a)}
    ib = {d: i for i, d in enumerate(dates_b)}
    xa = np.array([r_a[ia[d]] for d in communes])
    xb = np.array([r_b[ib[d]] for d in communes])
    return communes, xa, xb


def charger_cloture(ma2=True):
    """La chaine complete: CSV geles -> dates communes, rx (S&P), ry (CAC)."""
    series = {}
    for cle, nom in (("x", "spx.csv"), ("y", "cac.csv")):
        d, c = _lire_csv(nom)
        d, r = rendements_log(d, c)
        if ma2:
            d, r = paires(d, r)
        series[cle] = (d, r)
    return serie_appariee(*series["x"], *series["y"])
```

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_returns.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/returns.py tools/contagion/tests/test_returns.py
git commit  # "Rendements 2 jours apparies, la synchronisation traitee comme chez F-R"
```

---

### Task 4: `simulate.py` — le Monte-Carlo contre la formule

**Files:**
- Create: `tools/contagion/simulate.py`
- Test: `tools/contagion/tests/test_simulate.py`

- [ ] **Step 1: Écrire les tests (échouent)**

```python
# tools/contagion/tests/test_simulate.py
"""Le Monte-Carlo doit retomber sur la formule: c'est la validation du projet."""
import numpy as np
import pytest

from tools.contagion.bias import correction, delta_relatif, rho_conditionnelle
from tools.contagion.simulate import correlation, tirages

RHO, N, GRAINE = 0.58, 500_000, 20260814


def test_tirages_reproductibles_et_calibres():
    x1, y1 = tirages(RHO, N, GRAINE)
    x2, y2 = tirages(RHO, N, GRAINE)
    assert np.array_equal(x1, x2) and np.array_equal(y1, y2)
    assert correlation(x1, y1) == pytest.approx(RHO, abs=3 * (1 - RHO**2) / np.sqrt(N))


def test_conditionnement_suit_la_formule():
    """Correlation des sous-echantillons |x| >= quantile: la formule, pas plus."""
    x, y = tirages(RHO, N, GRAINE)
    var_pleine = x.var()
    for q in (0.5, 0.8, 0.95):
        seuil = np.sort(np.abs(x))[int(q * len(x))]
        garde = np.abs(x) >= seuil
        rho_obs = correlation(x[garde], y[garde])
        delta = delta_relatif(x[garde].var(), var_pleine)
        attendu = rho_conditionnelle(RHO, delta)
        tolerance = 3 * (1 - attendu**2) / np.sqrt(garde.sum())
        assert rho_obs == pytest.approx(attendu, abs=tolerance), q
        # et la correction retrouve la valeur vraie dans le meme intervalle
        assert correction(rho_obs, delta) == pytest.approx(RHO, abs=tolerance)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_simulate.py -q`
Expected: FAIL, module absent.

- [ ] **Step 3: Implémenter**

```python
# tools/contagion/simulate.py
"""Le monde temoin: un couple gaussien i.i.d. a correlation constante.

C'est la piece centrale de l'argument. Si la procedure des deciles fait monter
la correlation ICI, ou rien ne bouge par construction, alors la courbe montante
ne prouve rien en soi. La graine est fixee: la figure 2 est un calcul,
pas un alea.
"""
import numpy as np


def tirages(rho, n, graine):
    rng = np.random.default_rng(graine)
    x = rng.standard_normal(n)
    y = rho * x + np.sqrt(1.0 - rho * rho) * rng.standard_normal(n)
    return x, y


def correlation(x, y):
    """Pearson, diviseur n. Meme convention que l'explorateur JS: la parite en depend."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    cx, cy = x - x.mean(), y - y.mean()
    return float((cx * cy).mean() / np.sqrt(cx.var() * cy.var()))
```

Note : `np.var` est déjà en diviseur n ; `correlation` sert partout (déciles, export,
fixtures) pour qu'une seule définition existe côté Python.

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_simulate.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/simulate.py tools/contagion/tests/test_simulate.py
git commit  # "Monte-Carlo temoin: le conditionnement retombe sur la formule a 3 sigmas"
```

---

### Task 5: `deciles.py` — déciles de |x|, corrections, bootstrap

**Files:**
- Create: `tools/contagion/deciles.py`
- Test: `tools/contagion/tests/test_deciles.py`

- [ ] **Step 1: Écrire les tests (échouent)**

```python
# tools/contagion/tests/test_deciles.py
"""Les deciles portent les figures 1 a 3: leurs proprietes affichees sont testees ici."""
import numpy as np
import pytest

from tools.contagion.simulate import tirages
from tools.contagion.deciles import par_deciles

RHO, N, GRAINE = 0.58, 9000, 20260814


@pytest.fixture(scope="module")
def tranches():
    x, y = tirages(RHO, N, GRAINE)
    return par_deciles(x, y, graine_bootstrap=GRAINE)


def test_structure(tranches):
    assert len(tranches) == 10
    for t in tranches:
        for cle in ("rho", "rho_corrigee", "delta", "n", "amplitude_mediane",
                    "ic_bas", "ic_haut", "ic_corr_bas", "ic_corr_haut"):
            assert cle in t
    assert sum(t["n"] for t in tranches) == N


def test_courbe_brute_monte_courbe_corrigee_plate(tranches):
    bruts = [t["rho"] for t in tranches]
    assert bruts[-1] - bruts[0] > 0.3, "le biais doit se voir sur un monde a rho constant"
    corriges = [t["rho_corrigee"] for t in tranches]
    assert max(abs(c - RHO) for c in corriges) < 0.08, "la correction doit aplatir"


def test_bootstrap_reproductible_et_ordonne(tranches):
    x, y = tirages(RHO, N, GRAINE)
    bis = par_deciles(x, y, graine_bootstrap=GRAINE)
    assert [t["ic_bas"] for t in bis] == [t["ic_bas"] for t in tranches]
    for t in tranches:
        assert t["ic_bas"] < t["rho"] < t["ic_haut"]
        assert t["ic_corr_bas"] < t["rho_corrigee"] < t["ic_corr_haut"]
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_deciles.py -q`
Expected: FAIL, module absent.

- [ ] **Step 3: Implémenter**

```python
# tools/contagion/deciles.py
"""Correlation par decile d'amplitude du rendement source, brute et corrigee.

Le conditionnement est |x| CONTEMPORAIN, pas une volatilite glissante: c'est
la version pure du biais de selection, celle qui opere meme dans un monde
i.i.d. sans memoire, et donc celle que la figure du retournement exige. Chaque
point porte son intervalle a 95 % par bootstrap i.i.d. au sein du decile
(B = 2000, graine fixee); ce bootstrap ignore la dependance serielle et
sous-estime donc un peu la largeur, ce que la page dit en clair.
"""
import numpy as np

from tools.contagion.bias import correction, delta_relatif
from tools.contagion.simulate import correlation

B_BOOTSTRAP = 2000


def par_deciles(x, y, n_tranches=10, graine_bootstrap=20260814):
    x, y = np.asarray(x, float), np.asarray(y, float)
    var_pleine = x.var()
    ordre = np.argsort(np.abs(x), kind="stable")
    bornes = [round(i * len(x) / n_tranches) for i in range(n_tranches + 1)]
    rng = np.random.default_rng(graine_bootstrap)
    tranches = []
    for i in range(n_tranches):
        idx = ordre[bornes[i]:bornes[i + 1]]
        xb, yb = x[idx], y[idx]
        delta = delta_relatif(xb.var(), var_pleine)
        rho = correlation(xb, yb)
        tirage_rho, tirage_corr = [], []
        for _ in range(B_BOOTSTRAP):
            j = rng.integers(0, len(idx), len(idx))
            r = correlation(xb[j], yb[j])
            tirage_rho.append(r)
            tirage_corr.append(correction(r, delta_relatif(xb[j].var(), var_pleine)))
        bas, haut = np.percentile(tirage_rho, [2.5, 97.5])
        cbas, chaut = np.percentile(tirage_corr, [2.5, 97.5])
        tranches.append({
            "n": len(idx), "delta": delta, "rho": rho,
            "rho_corrigee": correction(rho, delta),
            "amplitude_mediane": float(np.median(np.abs(xb))),
            "ic_bas": float(bas), "ic_haut": float(haut),
            "ic_corr_bas": float(cbas), "ic_corr_haut": float(chaut),
        })
    return tranches
```

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_deciles.py -q`
Expected: PASS (3 tests). Durée ~ quelques secondes (20 000 corrélations de bootstrap).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/deciles.py tools/contagion/tests/test_deciles.py
git commit  # "Deciles d'amplitude avec correction et bootstrap, la brute monte, la corrigee non"
```

---

### Task 6: `rolling.py` — fenêtres glissantes pour la figure 4

**Files:**
- Create: `tools/contagion/rolling.py`
- Test: `tools/contagion/tests/test_rolling.py`

- [ ] **Step 1: Écrire les tests (échouent)**

```python
# tools/contagion/tests/test_rolling.py
import numpy as np
import pytest

from tools.contagion.simulate import correlation, tirages
from tools.contagion.rolling import glissantes

FENETRE = 60


def test_dimensions_et_premier_point():
    x, y = tirages(0.5, 300, 7)
    brute, corrigee, delta = glissantes(x, y, fenetre=FENETRE)
    assert len(brute) == len(corrigee) == len(delta) == 300 - FENETRE + 1
    assert brute[0] == pytest.approx(correlation(x[:FENETRE], y[:FENETRE]))


def test_sur_monde_constant_la_corrigee_reste_au_niveau():
    x, y = tirages(0.5, 20_000, 11)
    # variance locale gonflee artificiellement sur un segment: la brute doit monter,
    # la corrigee doit rester proche du niveau vrai EN MOYENNE sur le segment
    x2, y2 = x.copy(), y.copy()
    x2[8000:9000] *= 3.0
    y2[8000:9000] *= 3.0
    brute, corrigee, _ = glissantes(x2, y2, fenetre=FENETRE)
    segment = slice(8000 + FENETRE, 9000 - FENETRE)
    assert np.mean(brute[segment]) > 0.75
    assert abs(np.mean(corrigee[segment]) - 0.5) < 0.1
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_rolling.py -q`
Expected: FAIL, module absent.

- [ ] **Step 3: Implémenter**

```python
# tools/contagion/rolling.py
"""Correlation glissante brute et corrigee, pour la figure des deux crises.

Ici le conditionnement n'est plus |x| du jour mais la fenetre qui glisse: le
delta est l'exces de variance de la fenetre sur la variance pleine periode.
C'est la version la plus proche des usages de place, et celle ou le biais
opere par la persistance de la volatilite.
"""
import numpy as np

from tools.contagion.bias import correction, delta_relatif
from tools.contagion.simulate import correlation


def glissantes(x, y, fenetre=60):
    x, y = np.asarray(x, float), np.asarray(y, float)
    var_pleine = x.var()
    n = len(x) - fenetre + 1
    brute = np.empty(n)
    corrigee = np.empty(n)
    delta = np.empty(n)
    for i in range(n):
        xf, yf = x[i:i + fenetre], y[i:i + fenetre]
        brute[i] = correlation(xf, yf)
        delta[i] = delta_relatif(xf.var(), var_pleine)
        corrigee[i] = correction(brute[i], delta[i])
    return brute, corrigee, delta
```

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_rolling.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/rolling.py tools/contagion/tests/test_rolling.py
git commit  # "Correlation glissante corrigee: le delta vient de la fenetre elle-meme"
```

---

### Task 7: `export.py` — le JSON de la page et les fixtures de parité

**Files:**
- Create: `tools/contagion/export.py`
- Create: `assets/data/contagion.json` (produit)
- Create: `tools/js-tests/fixture-contagion.json` (produit)
- Test: `tools/contagion/tests/test_export.py`

- [ ] **Step 1: Écrire les tests (échouent)**

```python
# tools/contagion/tests/test_export.py
"""Le contrat entre Python et la page: contenu, budget, fixtures."""
import json
import pathlib

import pytest

from tools.contagion.export import construire, ecrire
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation

RACINE = pathlib.Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def artefacts():
    ecrire()
    donnees = json.loads((RACINE / "assets" / "data" / "contagion.json").read_text())
    fixture = json.loads((RACINE / "tools" / "js-tests" / "fixture-contagion.json").read_text())
    return donnees, fixture


def test_contenu_et_coherence(artefacts):
    donnees, _ = artefacts
    dates, rx, ry = charger_cloture()
    assert donnees["meta"]["n"] == len(rx) == len(donnees["rx"]) == len(donnees["ry"])
    assert donnees["meta"]["debut"] == dates[0] and donnees["meta"]["fin"] == dates[-1]
    # l'arrondi a 6 decimales ne doit pas deplacer la correlation avant la 5e
    rho_exact = correlation(rx, ry)
    rho_arrondi = correlation(donnees["rx"], donnees["ry"])
    assert abs(rho_exact - rho_arrondi) < 1e-5


def test_budget_de_taille(artefacts):
    octets = (RACINE / "assets" / "data" / "contagion.json").stat().st_size
    assert octets < 200_000, f"{octets} octets: budget ~150 Ko creve, spec section 12"


def test_fixtures_de_parite(artefacts):
    donnees, fixture = artefacts
    assert [c["q"] for c in fixture["cas"]] == [0.0, 0.5, 0.9]
    for cas in fixture["cas"]:
        for cle in ("n", "delta", "rho", "rho_corrigee"):
            assert cle in cas
    # les fixtures sont calculees sur les MEMES tableaux arrondis que le JSON servi
    assert fixture["rho_pleine"] == pytest.approx(
        correlation(donnees["rx"], donnees["ry"]), abs=1e-12)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_export.py -q`
Expected: FAIL, module absent.

- [ ] **Step 3: Implémenter**

```python
# tools/contagion/export.py
"""Ecrit assets/data/contagion.json et les fixtures de parite JS.

Usage: source .venv/bin/activate && python3 -m tools.contagion.export

Le JSON ne porte pas les dates: l'explorateur n'en a pas besoin, seules les
bornes vont dans meta (ecart assume a la spec, note dans le plan). Point
crucial de la parite: les fixtures sont calculees sur les tableaux ARRONDIS,
exactement ceux que le navigateur recevra, pas sur les flottants d'origine.
"""
import json
import pathlib

from tools.contagion.bias import correction, delta_relatif
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE_JSON = RACINE / "assets" / "data" / "contagion.json"
SORTIE_FIXTURE = RACINE / "tools" / "js-tests" / "fixture-contagion.json"
QUANTILES_FIXTURE = [0.0, 0.5, 0.9]


def sous_echantillon(rx, ry, q):
    """Convention unique du seuil, dupliquee a l'identique dans explorer.js."""
    ampl = sorted(abs(v) for v in rx)
    seuil = ampl[int(q * len(ampl))] if q > 0.0 else 0.0
    couples = [(a, b) for a, b in zip(rx, ry) if abs(a) >= seuil]
    return [a for a, _ in couples], [b for _, b in couples]


def construire():
    dates, rx, ry = charger_cloture()
    rx6 = [round(float(v), 6) for v in rx]
    ry6 = [round(float(v), 6) for v in ry]
    donnees = {
        "meta": {"source": "Yahoo Finance via yfinance, clotures quotidiennes, voir tools/contagion/data",
                 "series": "S&P 500 (x), CAC 40 (y), rendements log en moyenne mobile 2 j",
                 "debut": dates[0], "fin": dates[-1], "n": len(rx6)},
        "rx": rx6, "ry": ry6,
    }
    var_pleine = _variance(rx6)
    cas = []
    for q in QUANTILES_FIXTURE:
        sx, sy = sous_echantillon(rx6, ry6, q)
        delta = delta_relatif(_variance(sx), var_pleine)
        rho = correlation(sx, sy)
        cas.append({"q": q, "n": len(sx), "delta": delta, "rho": rho,
                    "rho_corrigee": correction(rho, delta)})
    fixture = {"rho_pleine": correlation(rx6, ry6), "cas": cas}
    return donnees, fixture


def _variance(valeurs):
    m = sum(valeurs) / len(valeurs)
    return sum((v - m) ** 2 for v in valeurs) / len(valeurs)


def ecrire():
    donnees, fixture = construire()
    SORTIE_JSON.write_text(json.dumps(donnees, separators=(",", ":")) + "\n")
    SORTIE_FIXTURE.write_text(json.dumps(fixture, indent=1) + "\n")
    print(SORTIE_JSON, SORTIE_JSON.stat().st_size, "octets")


if __name__ == "__main__":
    ecrire()
```

- [ ] **Step 4: Vérifier le passage, puis produire les artefacts**

Run: `python3 -m pytest tools/contagion/tests/test_export.py -q`
Expected: PASS (3 tests).
Run: `python3 -m tools.contagion.export` puis `git status --short` — les deux fichiers produits.

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/export.py tools/contagion/tests/test_export.py \
        assets/data/contagion.json tools/js-tests/fixture-contagion.json
git commit  # "Export du JSON de la page et des fixtures, calcules sur les tableaux arrondis"
```

---

### Task 8: `explorer.js` — le calcul côté navigateur, à parité

**Files:**
- Create: `assets/js/contagion/explorer.js`
- Test: `tools/js-tests/contagion.test.js`

- [ ] **Step 1: Écrire le test node (échoue)**

```javascript
// tools/js-tests/contagion.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { correlation, sousEchantillon, deltaRelatif, correctionFR, analyse }
  from '../../assets/js/contagion/explorer.js';

const fix = JSON.parse(readFileSync(new URL('./fixture-contagion.json', import.meta.url)));
const donnees = JSON.parse(readFileSync(new URL('../../assets/data/contagion.json', import.meta.url)));

test('la correlation pleine periode reproduit Python a 1e-9', () => {
  const rho = correlation(donnees.rx, donnees.ry);
  assert.ok(Math.abs(rho - fix.rho_pleine) < 1e-9, `${rho} vs ${fix.rho_pleine}`);
});

test('chaque cas de fixture est reproduit: n, delta, rho, correction', () => {
  for (const cas of fix.cas) {
    const r = analyse(donnees.rx, donnees.ry, cas.q);
    assert.equal(r.n, cas.n, `n a q=${cas.q}`);
    for (const cle of ['delta', 'rho', 'rho_corrigee']) {
      assert.ok(Math.abs(r[cle] - cas[cle]) < 1e-9, `${cle} a q=${cas.q}: ${r[cle]} vs ${cas[cle]}`);
    }
  }
});

test('les briques sont coherentes entre elles', () => {
  const { rx, ry } = donnees;
  const [sx, sy] = sousEchantillon(rx, ry, 0.5);
  const delta = deltaRelatif(sx, rx);
  const rho = correlation(sx, sy);
  const r = analyse(rx, ry, 0.5);
  assert.equal(r.n, sx.length);
  assert.ok(Math.abs(correctionFR(rho, delta) - r.rho_corrigee) < 1e-15);
});
```

- [ ] **Step 2: Vérifier l'échec**

Run: `node --test tools/js-tests/`
Expected: les tests eclipse passent, les trois nouveaux échouent (module absent).

- [ ] **Step 3: Implémenter**

```javascript
// assets/js/contagion/explorer.js
// Le calcul de l'explorateur, sans DOM: correlation, seuil de quantile, delta,
// correction de Forbes-Rigobon. Ce module est importe par la page ET par le
// test node contre les fixtures Python: les memes conventions exactement
// (diviseur n, seuil = valeur triee d'indice floor(q*n), garde si |x| >= seuil).

export function correlation(xs, ys) {
  const n = xs.length;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
  mx /= n; my /= n;
  let cxy = 0, vx = 0, vy = 0;
  for (let i = 0; i < n; i++) {
    const a = xs[i] - mx, b = ys[i] - my;
    cxy += a * b; vx += a * a; vy += b * b;
  }
  return (cxy / n) / Math.sqrt((vx / n) * (vy / n));
}

export function variance(xs) {
  const n = xs.length;
  let m = 0;
  for (let i = 0; i < n; i++) m += xs[i];
  m /= n;
  let v = 0;
  for (let i = 0; i < n; i++) { const d = xs[i] - m; v += d * d; }
  return v / n;
}

export function sousEchantillon(rx, ry, q) {
  if (q <= 0) return [rx.slice(), ry.slice()];
  const ampl = rx.map(Math.abs).sort((a, b) => a - b);
  const seuil = ampl[Math.floor(q * ampl.length)];
  const sx = [], sy = [];
  for (let i = 0; i < rx.length; i++) {
    if (Math.abs(rx[i]) >= seuil) { sx.push(rx[i]); sy.push(ry[i]); }
  }
  return [sx, sy];
}

export function deltaRelatif(sousX, pleinX) {
  return variance(sousX) / variance(pleinX) - 1;
}

export function correctionFR(rhoCond, delta) {
  return rhoCond / Math.sqrt(1 + delta * (1 - rhoCond * rhoCond));
}

export function analyse(rx, ry, q) {
  const [sx, sy] = sousEchantillon(rx, ry, q);
  const delta = deltaRelatif(sx, rx);
  const rho = correlation(sx, sy);
  return { n: sx.length, delta, rho, rho_corrigee: correctionFR(rho, delta) };
}
```

- [ ] **Step 4: Vérifier le passage**

Run: `node --test tools/js-tests/`
Expected: PASS, anciens et nouveaux tests. Si un écart dépasse 1e-9 : vérifier que
`sous_echantillon` Python et `sousEchantillon` JS trient et seuillent à l'identique
(indice `floor(q*n)`, comparaison `>=`), et que les deux lisent bien les tableaux arrondis.

- [ ] **Step 5: Commit**

```bash
git add assets/js/contagion/explorer.js tools/js-tests/contagion.test.js
git commit  # "Le calcul de l'explorateur en JS, a parite 1e-9 avec Python sur fixtures"
```

---

### Task 9: `figures.py` — charpente commune et figure 1 (le constat)

Le module suit `tools/eclipse/figures.py` : SVG écrit à la main, hérité des variables CSS,
injecté entre `<!-- fig:… -->` et `<!-- /fig:… -->`, vue tabulaire sous `<details>`.
Cette tâche pose la charpente (repères, axes, formats, injection) et livre la figure 1 ;
les tâches 10 et 11 réutilisent la charpente.

**Files:**
- Create: `tools/contagion/figures.py`
- Test: `tools/contagion/tests/test_figures.py`

- [ ] **Step 1: Écrire les tests de la charpente et de la figure 1 (échouent)**

```python
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
    assert figures.pourcent(92.123, "fr", 1) == "92,1 %"
    assert figures.pourcent(92.123, "en", 1) == "92.1 %"


def test_pas_de_tiret_cadratin(contexte):
    for lang in ("fr", "en"):
        assert "—" not in figures.fig_constat(contexte, lang)
```

Avant d'écrire `pourcent`, ouvrir `tools/eclipse/figures.py` et reprendre le même
caractère insécable que lui (U+202F attendu) ; si l'éclipse utilise U+00A0, aligner le
test et la fonction sur l'existant : une seule convention sur le site.

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_figures.py -q`
Expected: FAIL, module absent.

- [ ] **Step 3: Implémenter la charpente et la figure 1**

```python
# tools/contagion/figures.py
"""Les quatre figures SVG de la page contagion, calculees puis injectees.

Meme doctrine que tools/eclipse/figures.py, dont ce module reprend les
conventions (SVG en ligne pour heriter des deux themes, vue tabulaire sous
<details>, injection entre reperes, aucune valeur saisie a la main). Les
couleurs de serie reprennent le couple valide de l'eclipse: l'accent vert du
site tombe sous le plancher de chroma des qu'il porte une courbe.
"""
import pathlib
import re

from tools.contagion import rolling
from tools.contagion.deciles import par_deciles
from tools.contagion.returns import charger_cloture
from tools.contagion.simulate import correlation, tirages
from tools.contagion.bias import rho_conditionnelle

RACINE = pathlib.Path(__file__).resolve().parents[2]
PAGES = {
    "fr": RACINE / "projets" / "contagion.html",
    "en": RACINE / "en" / "projects" / "contagion.html",
}
GRAINE = 20260814

# Geometrie commune: viewBox 640 de large, zone de trace x dans [54, 528],
# memes marges que les figures de l'eclipse pour que l'oeil retrouve la grille.
X0, X1 = 54.0, 528.0
# Couleurs: reprendre les DEUX memes classes CSS de serie que l'eclipse
# (.fig-serie-a, .fig-serie-b dans style.css); pas de couleur en dur ici.


def nombre(x, lang, dec):
    s = f"{x:.{dec}f}"
    return s.replace(".", ",") if lang == "fr" else s


def pourcent(x, lang, dec):
    return nombre(x, lang, dec) + " %"


def sx(v, v0, v1):
    """Abscisse SVG d'une valeur v sur [v0, v1]."""
    return round(X0 + (v - v0) / (v1 - v0) * (X1 - X0), 2)


def sy(v, v0, v1, y0, y1):
    """Ordonnee SVG (axe inverse) d'une valeur v sur [v0, v1] trace entre y0 et y1."""
    return round(y1 - (v - v0) / (v1 - v0) * (y1 - y0), 2)


def calculer():
    """Tout le calcul des quatre figures, une seule fois."""
    dates, rx, ry = charger_cloture()
    rho_pleine = correlation(rx, ry)
    tranches_reelles = par_deciles(rx, ry, graine_bootstrap=GRAINE)
    xs, ys = tirages(rho_pleine, len(rx), GRAINE)
    tranches_simulees = par_deciles(xs, ys, graine_bootstrap=GRAINE)
    brute, corrigee, delta = rolling.glissantes(rx, ry, fenetre=60)
    return {
        "dates": dates, "rx": rx, "ry": ry, "rho_pleine": rho_pleine,
        "tranches_reelles": tranches_reelles,
        "tranches_simulees": tranches_simulees,
        "glissante": {"dates": dates[59:], "brute": brute, "corrigee": corrigee},
    }


def _tranches_svg(tranches, rho_reference, lang, id_fig, titre, description,
                  serie_b=None, courbe_analytique=None):
    """Le rendu commun aux figures 1 a 3: deciles en x, correlation en y.

    serie_b: seconde liste de valeurs par decile (figure 3, courbe corrigee).
    courbe_analytique: liste de valeurs par decile a tracer en trait fin
    (figure 2, la prediction de la formule).
    """
    y0, y1 = 32.0, 320.0
    v0, v1 = 0.0, 1.0
    xs_dec = [sx(i + 0.5, 0, 10) for i in range(10)]
    parts = [f'<figure class="fig" id="{id_fig}">']
    parts.append(f'<svg class="fig-svg" viewBox="0 0 640 388" role="img" '
                 f'aria-labelledby="{id_fig}-t {id_fig}-d">')
    parts.append(f'<title id="{id_fig}-t">{titre}</title>')
    parts.append(f'<desc id="{id_fig}-d">{description}</desc>')
    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = sy(v, v0, v1, y0, y1)
        parts.append(f'<line class="fig-grille" x1="{X0}" y1="{y}" x2="{X1}" y2="{y}"/>')
        parts.append(f'<text class="fig-tick fig-tick-y" x="{X0 - 8}" y="{y + 4}">'
                     f'{nombre(v, lang, 2)}</text>')
    yref = sy(rho_reference, v0, v1, y0, y1)
    parts.append(f'<polyline class="fig-repere" points="{X0},{yref} {X1},{yref}"/>')
    if courbe_analytique is not None:
        pts = " ".join(f"{x},{sy(v, v0, v1, y0, y1)}"
                       for x, v in zip(xs_dec, courbe_analytique))
        parts.append(f'<polyline class="fig-trait fig-serie-b" points="{pts}"/>')
    for x, t in zip(xs_dec, tranches):
        ybas, yhaut = sy(t["ic_bas"], v0, v1, y0, y1), sy(t["ic_haut"], v0, v1, y0, y1)
        parts.append(f'<line class="fig-ic fig-serie-a" x1="{x}" y1="{ybas}" '
                     f'x2="{x}" y2="{yhaut}"/>')
        parts.append(f'<circle class="fig-point fig-serie-a" cx="{x}" '
                     f'cy="{sy(t["rho"], v0, v1, y0, y1)}" r="4"/>')
    if serie_b is not None:
        for x, t in zip(xs_dec, tranches):
            ybas = sy(t["ic_corr_bas"], v0, v1, y0, y1)
            yhaut = sy(t["ic_corr_haut"], v0, v1, y0, y1)
            parts.append(f'<line class="fig-ic fig-serie-b" x1="{x + 6}" y1="{ybas}" '
                         f'x2="{x + 6}" y2="{yhaut}"/>')
            parts.append(f'<circle class="fig-point fig-serie-b" cx="{x + 6}" '
                         f'cy="{sy(t["rho_corrigee"], v0, v1, y0, y1)}" r="4"/>')
    for i, t in enumerate(tranches):
        parts.append(f'<text class="fig-tick" x="{xs_dec[i]}" y="{y1 + 18}" '
                     f'text-anchor="middle">{i + 1}</text>')
    axe = ("décile de |rendement S&P|, amplitude médiane en dessous" if lang == "fr"
           else "decile of |S&P return|, median magnitude below")
    parts.append(f'<text class="fig-tick" x="{(X0 + X1) / 2}" y="{y1 + 52}" '
                 f'text-anchor="middle">{axe}</text>')
    for i in (0, 4, 9):
        ampl = pourcent(tranches[i]["amplitude_mediane"] * 100, lang, 2)
        parts.append(f'<text class="fig-tick" x="{xs_dec[i]}" y="{y1 + 34}" '
                     f'text-anchor="middle">{ampl}</text>')
    parts.append("</svg>")
    parts.append(_tableau(tranches, lang, avec_corrigee=serie_b is not None))
    parts.append("</figure>")
    return "\n".join(parts)


def _tableau(tranches, lang, avec_corrigee):
    t_ouvre = ("les valeurs des tracés" if lang == "fr" else "the plotted values")
    entetes_fr = ["Décile", "n", "Amplitude médiane", "δ", "Corrélation"]
    entetes_en = ["Decile", "n", "Median magnitude", "δ", "Correlation"]
    entetes = entetes_fr if lang == "fr" else entetes_en
    if avec_corrigee:
        entetes.append("Corrigée" if lang == "fr" else "Corrected")
    lignes = []
    for i, t in enumerate(tranches):
        cases = [str(i + 1), str(t["n"]),
                 pourcent(t["amplitude_mediane"] * 100, lang, 2),
                 nombre(t["delta"], lang, 2), nombre(t["rho"], lang, 3)]
        if avec_corrigee:
            cases.append(nombre(t["rho_corrigee"], lang, 3))
        lignes.append("<tr>" + "".join(f"<td>{c}</td>" for c in cases) + "</tr>")
    return ("<details><summary>" + t_ouvre + "</summary><table><thead><tr>"
            + "".join(f"<th>{e}</th>" for e in entetes)
            + "</tr></thead><tbody>" + "".join(lignes) + "</tbody></table></details>")


def fig_constat(ctx, lang):
    titre = ("Corrélation S&P 500 × CAC 40 par décile d'amplitude" if lang == "fr"
             else "S&P 500 × CAC 40 correlation by magnitude decile")
    desc = ("La corrélation d'échantillon monte du premier au dernier décile "
            "d'amplitude du rendement S&P ; la droite horizontale est la "
            "corrélation pleine période." if lang == "fr" else
            "Sample correlation rises from the first to the last decile of "
            "S&P return magnitude; the horizontal line is the full-sample "
            "correlation.")
    return _tranches_svg(ctx["tranches_reelles"], ctx["rho_pleine"], lang,
                         "fig-constat", titre, desc)


def injecter(chemin, bloc, contenu):
    """Remplace ce qui se trouve entre <!-- fig:bloc --> et <!-- /fig:bloc -->."""
    texte = chemin.read_text(encoding="utf-8")
    motif = re.compile(rf"(<!-- fig:{bloc} -->).*?(<!-- /fig:{bloc} -->)", re.S)
    if not motif.search(texte):
        raise SystemExit(f"reperes <!-- fig:{bloc} --> absents de {chemin}")
    texte = motif.sub(lambda m: m.group(1) + "\n" + contenu + "\n" + m.group(2), texte)
    chemin.write_text(texte, encoding="utf-8")
```

Vérifier au passage dans `assets/style.css` que les classes `.fig`, `.fig-svg`,
`.fig-grille`, `.fig-tick`, `.fig-repere`, `.fig-trait`, `.fig-point` existent déjà
(figures de l'éclipse) ; ajouter dans la même section les classes manquantes
(`.fig-ic`, `.fig-serie-a`, `.fig-serie-b`) avec les deux couleurs de série reprises des
figures de l'éclipse.

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_figures.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/figures.py tools/contagion/tests/test_figures.py assets/style.css
git commit  # "Charpente des figures contagion et figure du constat, deciles reels"
```

---

### Task 10: figures 2 et 3 — le retournement et la correction

**Files:**
- Modify: `tools/contagion/figures.py`
- Test: `tools/contagion/tests/test_figures.py` (ajouts)

- [ ] **Step 1: Ajouter les tests (échouent)**

```python
# a ajouter a tools/contagion/tests/test_figures.py

def test_fig2_le_monde_constant_monte_aussi(contexte):
    simulees = [t["rho"] for t in contexte["tranches_simulees"]]
    assert simulees[-1] - simulees[0] > 0.25


def test_fig2_analytique_colle_au_monte_carlo(contexte):
    from tools.contagion.bias import rho_conditionnelle
    for t in contexte["tranches_simulees"]:
        attendu = rho_conditionnelle(contexte["rho_pleine"], t["delta"])
        assert t["ic_bas"] < attendu < t["ic_haut"], "la formule sort de l'IC bootstrap"


def test_fig3_ecart_maximal_de_la_corrigee(contexte):
    corrigees = [t["rho_corrigee"] for t in contexte["tranches_reelles"]]
    ecart = max(abs(c - contexte["rho_pleine"]) for c in corrigees)
    # la legende cite cet ecart: le test verrouille qu'il reste tres en dessous
    # de la montee de la courbe brute
    bruts = [t["rho"] for t in contexte["tranches_reelles"]]
    assert ecart < (bruts[-1] - bruts[0]) / 3


def test_fig2_fig3_svg_bien_formes(contexte):
    for fabrique in (figures.fig_retournement, figures.fig_correction):
        for lang in ("fr", "en"):
            svg = fabrique(contexte, lang)
            assert svg.count("<svg") == 1 and "aria-labelledby" in svg
            assert "—" not in svg
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_figures.py -q`
Expected: FAIL, `fig_retournement` absent (les deux tests de calcul peuvent déjà passer).

- [ ] **Step 3: Implémenter les deux figures**

```python
# a ajouter a tools/contagion/figures.py

def fig_retournement(ctx, lang):
    analytique = [rho_conditionnelle(ctx["rho_pleine"], t["delta"])
                  for t in ctx["tranches_simulees"]]
    titre = ("La même procédure sur un monde à corrélation constante" if lang == "fr"
             else "The same procedure on a constant-correlation world")
    desc = ("Couple gaussien simulé, corrélation vraie constante égale à la "
            "pleine période du couple réel : la courbe par décile monte de la "
            "même façon, et suit la prédiction analytique tracée en trait "
            "fin." if lang == "fr" else
            "Simulated Gaussian pair with constant true correlation set to the "
            "real pair's full-sample value: the decile curve rises the same "
            "way, and follows the analytic prediction drawn as a thin line.")
    return _tranches_svg(ctx["tranches_simulees"], ctx["rho_pleine"], lang,
                         "fig-retournement", titre, desc,
                         courbe_analytique=analytique)


def fig_correction(ctx, lang):
    titre = ("Les déciles réels, bruts et corrigés" if lang == "fr"
             else "Real deciles, raw and corrected")
    desc = ("Les mêmes déciles que la première figure, avec la correction de "
            "Forbes et Rigobon : la courbe corrigée reste au voisinage de la "
            "corrélation pleine période." if lang == "fr" else
            "Same deciles as the first figure, with the Forbes-Rigobon "
            "correction: the corrected curve stays near the full-sample "
            "correlation.")
    return _tranches_svg(ctx["tranches_reelles"], ctx["rho_pleine"], lang,
                         "fig-correction", titre, desc, serie_b=True)
```

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_figures.py -q`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/figures.py tools/contagion/tests/test_figures.py
git commit  # "Figures du retournement et de la correction, l'analytique dans l'IC du Monte-Carlo"
```

---

### Task 11: figure 4 — ce qui reste de 2008 et de 2020

**Files:**
- Modify: `tools/contagion/figures.py`
- Test: `tools/contagion/tests/test_figures.py` (ajouts)

- [ ] **Step 1: Ajouter les tests (échouent)**

```python
# a ajouter a tools/contagion/tests/test_figures.py

EPISODES = [("2008-09-01", "2008-12-31"), ("2020-02-15", "2020-04-30")]


def _moyenne_episode(ctx, serie, debut, fin):
    g = ctx["glissante"]
    valeurs = [v for d, v in zip(g["dates"], g[serie]) if debut <= d <= fin]
    assert len(valeurs) > 20, "episode absent des donnees"
    return sum(valeurs) / len(valeurs)


def test_fig4_la_brute_monte_dans_les_deux_crises(contexte):
    for debut, fin in EPISODES:
        assert _moyenne_episode(contexte, "brute", debut, fin) > \
            contexte["rho_pleine"] + 0.1


def test_fig4_la_correction_reduit_l_exces(contexte):
    for debut, fin in EPISODES:
        exces_brut = _moyenne_episode(contexte, "brute", debut, fin) - contexte["rho_pleine"]
        exces_corrige = _moyenne_episode(contexte, "corrigee", debut, fin) - contexte["rho_pleine"]
        assert exces_corrige < exces_brut, (debut, "la correction n'a rien reduit")
        # PAS d'assertion exces_corrige ~ 0: ce qui reste est le contenu de la page,
        # la legende citera la valeur qui sort, quelle qu'elle soit (spec, section 12)


def test_fig4_svg_bien_forme(contexte):
    for lang in ("fr", "en"):
        svg = figures.fig_reste(contexte, lang)
        assert svg.count("<svg") == 1 and "aria-labelledby" in svg
        assert svg.count('class="fig-episode"') == 2
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_figures.py -q`
Expected: FAIL, `fig_reste` absent.

- [ ] **Step 3: Implémenter**

```python
# a ajouter a tools/contagion/figures.py

EPISODES = [("2008-09-01", "2008-12-31"), ("2020-02-15", "2020-04-30")]


def fig_reste(ctx, lang):
    g = ctx["glissante"]
    dates, brute, corrigee = g["dates"], g["brute"], g["corrigee"]
    y0, y1 = 32.0, 320.0
    v0, v1 = -0.4, 1.0
    n = len(dates)
    annees = [d[:4] for d in dates]

    def x_de(i):
        return round(X0 + i / (n - 1) * (X1 - X0), 2)

    titre = ("Corrélation glissante 60 jours, brute et corrigée" if lang == "fr"
             else "60-day rolling correlation, raw and corrected")
    desc = ("De 1991 à 2026, la corrélation glissante brute et sa version "
            "corrigée du delta de la fenêtre ; 2008 et le début 2020 sont "
            "surlignés." if lang == "fr" else
            "From 1991 to 2026, raw rolling correlation and its version "
            "corrected for the window's delta; 2008 and early 2020 are "
            "highlighted.")
    parts = [f'<figure class="fig" id="fig-reste">',
             f'<svg class="fig-svg" viewBox="0 0 640 388" role="img" '
             f'aria-labelledby="fig-reste-t fig-reste-d">',
             f'<title id="fig-reste-t">{titre}</title>',
             f'<desc id="fig-reste-d">{desc}</desc>']
    for debut, fin in EPISODES:
        i0 = min(i for i, d in enumerate(dates) if d >= debut)
        i1 = max(i for i, d in enumerate(dates) if d <= fin)
        parts.append(f'<rect class="fig-episode" x="{x_de(i0)}" y="{y0}" '
                     f'width="{round(x_de(i1) - x_de(i0), 2)}" height="{y1 - y0}"/>')
    for v in (-0.25, 0.0, 0.25, 0.5, 0.75, 1.0):
        y = sy(v, v0, v1, y0, y1)
        parts.append(f'<line class="fig-grille" x1="{X0}" y1="{y}" x2="{X1}" y2="{y}"/>')
        parts.append(f'<text class="fig-tick fig-tick-y" x="{X0 - 8}" y="{y + 4}">'
                     f'{nombre(v, lang, 2)}</text>')
    # sous-echantillonnage d'affichage: un point tous les 5 jours suffit a l'ecran
    # et divise par cinq le poids de la page (les tests, eux, portent sur les series pleines)
    for serie, classe in (("brute", "fig-serie-a"), ("corrigee", "fig-serie-b")):
        pts = " ".join(f"{x_de(i)},{sy(g[serie][i], v0, v1, y0, y1)}"
                       for i in range(0, n, 5))
        parts.append(f'<polyline class="fig-trait {classe}" points="{pts}"/>')
    derniere = ""
    for i in range(0, n, 250):
        if annees[i] != derniere and int(annees[i]) % 5 == 0:
            parts.append(f'<text class="fig-tick" x="{x_de(i)}" y="{y1 + 18}" '
                         f'text-anchor="middle">{annees[i]}</text>')
            derniere = annees[i]
    parts.append("</svg>")
    lignes = []
    for (debut, fin), nom_fr, nom_en in zip(EPISODES, ("automne 2008", "février-avril 2020"),
                                            ("autumn 2008", "february-april 2020")):
        sel = [i for i, d in enumerate(dates) if debut <= d <= fin]
        mb = sum(brute[i] for i in sel) / len(sel)
        mc = sum(corrigee[i] for i in sel) / len(sel)
        nom = nom_fr if lang == "fr" else nom_en
        lignes.append(f"<tr><td>{nom}</td><td>{nombre(mb, lang, 3)}</td>"
                      f"<td>{nombre(mc, lang, 3)}</td></tr>")
    t_ouvre = "les moyennes par épisode" if lang == "fr" else "episode averages"
    e1 = "Épisode" if lang == "fr" else "Episode"
    e2 = "Brute" if lang == "fr" else "Raw"
    e3 = "Corrigée" if lang == "fr" else "Corrected"
    parts.append(f"<details><summary>{t_ouvre}</summary><table><thead>"
                 f"<tr><th>{e1}</th><th>{e2}</th><th>{e3}</th></tr></thead>"
                 f"<tbody>{''.join(lignes)}</tbody></table></details>")
    parts.append("</figure>")
    return "\n".join(parts)
```

Ajouter à `assets/style.css`, dans la section des figures, la classe `.fig-episode`
(remplissage discret à ~8 % d'opacité de l'encre, aucun trait).

- [ ] **Step 4: Vérifier le passage**

Run: `python3 -m pytest tools/contagion/tests/test_figures.py -q`
Expected: PASS (12 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/figures.py tools/contagion/tests/test_figures.py assets/style.css
git commit  # "Figure des deux crises: la correction reduit l'exces, le reste est le sujet"
```

---

### Task 12: les deux pages HTML — squelettes avec repères, et `build.py`

Les pages naissent avec leurs repères `<!-- fig:… -->` vides et une prose de premier jet ;
`build.py` calcule tout, injecte les quatre figures dans les deux pages, et écrit les
artefacts. La prose définitive est la tâche 14.

**Files:**
- Create: `projets/contagion.html`
- Create: `en/projects/contagion.html`
- Create: `tools/contagion/build.py`
- Test: `tools/contagion/tests/test_build.py`

- [ ] **Step 1: Écrire le test d'injection (échoue)**

```python
# tools/contagion/tests/test_build.py
"""L'injection est complete et idempotente, dans les deux pages."""
import pathlib

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
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_build.py -q`
Expected: FAIL, pages absentes.

- [ ] **Step 3: Créer les deux squelettes**

`projets/contagion.html` — tête et enveloppe calquées sur `projets/eclipse.html` (mêmes
balises : canonical + hreflang croisés vers `/en/projects/contagion.html`, OG vers
`assets/og/contagion.jpg`, `og:type` article, `body class="article post"`, header quatre
éléments avec `projets` actif, footer standard, script GoatCounter). Corps :

```html
<main class="wrap">
  <p class="post-date"><time datetime="⟨date de publication⟩">⟨date en toutes lettres⟩</time></p>
  <h1>La contagion, ou moins qu'on ne dit</h1>
  <p class="standfirst">« Quand ça va mal, les corrélations montent vers 1. » La phrase est
  répétée partout en gestion, et le graphe qui la prouve se recalcule en une page. Une bonne
  partie de ce qu'il montre est un artefact d'échantillonnage, et la part se mesure.</p>
  <p class="facts"><b>Mots-clés</b> <span>S&amp;P 500 × CAC 40</span>
    <span>Forbes-Rigobon 2002</span>
    <span>⟨n⟩ jours de cotation</span>
    <span>corrélations conditionnelles</span>
    <span>sans dépendance</span></p>

  <h2>Le constat</h2>
  <p>⟨premier jet §1 : les données, la procédure des déciles, la courbe qui monte,
  au premier degré⟩</p>
  <!-- fig:constat -->
  <!-- /fig:constat -->

  <h2>Le retournement</h2>
  <p>⟨premier jet §2 : le monde simulé à corrélation constante, même procédure,
  même courbe⟩</p>
  <!-- fig:retournement -->
  <!-- /fig:retournement -->

  <h2>Le mécanisme</h2>
  <p>⟨premier jet §3 : beta ne bouge pas, le rapport signal sur bruit bouge ;
  la formule, la dérivation sous details⟩</p>

  <h2>La correction</h2>
  <p>⟨premier jet §4 : l'inversion de Forbes-Rigobon⟩</p>
  <!-- fig:correction -->
  <!-- /fig:correction -->
  <!-- explorateur: pose a la tache 13 -->

  <h2>Ce qui reste</h2>
  <p>⟨premier jet §5 : 2008 et 2020, brute contre corrigée, la valeur qui sort⟩</p>
  <!-- fig:reste -->
  <!-- /fig:reste -->

  <h2>Ce que le calcul suppose</h2>
  <ul>
    <li>⟨liste d'honnêteté, six points, spec §9⟩</li>
  </ul>

  <p class="byline">Publié par Vincent Nazzareno le <time datetime="⟨date⟩">⟨date⟩</time>.</p>
  <p class="backlink"><a href="/#projets">← retour aux projets</a></p>
</main>
```

`en/projects/contagion.html` — même squelette, langue `en`, header/footer version EN
(calqués sur `en/projects/eclipse.html`), titre « Contagion, or less than advertised »,
liens hreflang croisés inverses.

- [ ] **Step 4: Écrire `build.py`**

```python
# tools/contagion/build.py
"""Orchestration complete: calcul, injection des figures, export des artefacts.

Usage: source .venv/bin/activate && python3 -m tools.contagion.build

Idempotent par construction: relancer sans changement de code ni de donnees
reecrit exactement les memes octets (graines fixees, injection entre reperes).
"""
from tools.contagion import export, figures


def main():
    ctx = figures.calculer()
    fabriques = {
        "constat": figures.fig_constat,
        "retournement": figures.fig_retournement,
        "correction": figures.fig_correction,
        "reste": figures.fig_reste,
    }
    for lang, chemin in figures.PAGES.items():
        for bloc, fabrique in fabriques.items():
            figures.injecter(chemin, bloc, fabrique(ctx, lang))
        print(chemin.name, "figures injectees")
    export.ecrire()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Vérifier le passage, construire, regarder**

Run: `python3 -m pytest tools/contagion/tests/test_build.py -q`
Expected: PASS (2 tests).
Run: `python3 -m tools.contagion.build && python3 -m http.server 8777 &` puis ouvrir
`http://localhost:8777/projets/contagion.html` : quatre figures visibles dans les deux
thèmes, tableaux dépliables. Arrêter le serveur.

- [ ] **Step 6: Commit**

```bash
git add projets/contagion.html en/projects/contagion.html tools/contagion/build.py \
        tools/contagion/tests/test_build.py assets/data/contagion.json
git commit  # "Squelettes des deux pages contagion et build d'injection idempotent"
```

---

### Task 13: l'explorateur dans la page — `ui.js`, styles, accessibilité

**Files:**
- Create: `assets/js/contagion/ui.js`
- Modify: `projets/contagion.html`, `en/projects/contagion.html` (bloc explorateur)
- Modify: `assets/style.css` (styles `.explorateur`)

- [ ] **Step 1: Poser le bloc HTML dans les deux pages**

À la place du repère `<!-- explorateur: … -->`, dans la page FR :

```html
<div class="explorateur" id="explorateur" hidden>
  <p class="explo-titre">Déplacez le seuil : la brute grimpe, la corrigée reste posée.</p>
  <label for="explo-seuil">Garder les jours où |rendement S&amp;P| dépasse le
  quantile <output id="explo-q">0,50</output></label>
  <input type="range" id="explo-seuil" min="0" max="95" step="5" value="50">
  <div class="explo-barres" aria-hidden="true">
    <div class="explo-ligne"><span>brute</span><div class="explo-barre explo-a"></div></div>
    <div class="explo-ligne"><span>corrigée</span><div class="explo-barre explo-b"></div></div>
  </div>
  <output id="explo-valeurs" aria-live="polite"></output>
</div>
<noscript><p>Sans JavaScript, cet encart n'a rien à montrer que la figure ci-dessus ne
montre déjà : au-dessus du quantile 0,90, la corrélation brute vaut ⟨valeur⟩ et la
corrigée ⟨valeur⟩, pour une pleine période à ⟨valeur⟩.</p></noscript>
<script type="module" src="/assets/js/contagion/ui.js"></script>
```

Version EN équivalente (« raw », « corrected », mêmes ids). Les ⟨valeurs⟩ du `noscript`
viennent de `tools/js-tests/fixture-contagion.json` (cas q = 0,9) et seront verrouillées
par le test de prose de la tâche 14. Le bloc est `hidden` et révélé par `ui.js` : sans
JavaScript, seuls la figure et le `noscript` existent.

- [ ] **Step 2: Écrire `ui.js`**

```javascript
// assets/js/contagion/ui.js
// L'enveloppe DOM de l'explorateur: chargement du JSON, curseur, affichage.
// Tout le calcul est dans explorer.js, teste sous node; ici il n'y a que la page.
import { analyse, correlation } from './explorer.js';

const bloc = document.getElementById('explorateur');
if (bloc) init().catch(() => { /* sans donnees, le noscript et la figure suffisent */ });

async function init() {
  const reponse = await fetch('/assets/data/contagion.json');
  if (!reponse.ok) return;
  const { rx, ry } = await reponse.json();
  const pleine = correlation(rx, ry);
  const fr = document.documentElement.lang === 'fr';
  const nombre = (v, dec) => fr ? v.toFixed(dec).replace('.', ',') : v.toFixed(dec);
  const curseur = document.getElementById('explo-seuil');
  const sortieQ = document.getElementById('explo-q');
  const valeurs = document.getElementById('explo-valeurs');
  const barreA = bloc.querySelector('.explo-a');
  const barreB = bloc.querySelector('.explo-b');

  function rendre() {
    const q = Number(curseur.value) / 100;
    const r = analyse(rx, ry, q);
    sortieQ.textContent = nombre(q, 2);
    barreA.style.width = `${Math.max(0, r.rho) * 100}%`;
    barreB.style.width = `${Math.max(0, r.rho_corrigee) * 100}%`;
    valeurs.textContent = fr
      ? `${r.n} jours gardés · δ = ${nombre(r.delta, 2)} · brute ${nombre(r.rho, 3)} · `
        + `corrigée ${nombre(r.rho_corrigee, 3)} · pleine période ${nombre(pleine, 3)}`
      : `${r.n} days kept · δ = ${nombre(r.delta, 2)} · raw ${nombre(r.rho, 3)} · `
        + `corrected ${nombre(r.rho_corrigee, 3)} · full sample ${nombre(pleine, 3)}`;
  }

  curseur.addEventListener('input', rendre);
  bloc.hidden = false;
  rendre();
}
```

- [ ] **Step 3: Styles dans `assets/style.css`**

Dans une section `/* ---- explorateur contagion ---- */` à la suite des styles de
figures : `.explorateur` (bordure `1px solid var(--rule)`, padding, fond `var(--paper)`),
`.explo-barre` (hauteur 0.75rem, transition width 0.15s ease, couleurs des deux séries
reprises de `.fig-serie-a`/`.fig-serie-b`), `.explo-ligne` (grid `6rem 1fr`, étiquettes en
`var(--mono)` petite taille), `input[type="range"]` pleine largeur, `#explo-valeurs` en
`var(--mono)` `0.8125rem`. Respecter `prefers-reduced-motion` : transition supprimée sous
`@media (prefers-reduced-motion: reduce)`.

- [ ] **Step 4: Vérifier**

Run: `node --test tools/js-tests/` — toujours PASS (ui.js n'est pas importé par les tests).
Run: `python3 -m http.server 8777 &` — sur la page FR et la page EN : le curseur au
clavier (flèches), les valeurs qui suivent, la barre brute qui monte avec q, l'`aria-live`
qui annonce, le bloc absent quand JavaScript est coupé. Arrêter le serveur.

- [ ] **Step 5: Commit**

```bash
git add assets/js/contagion/ui.js projets/contagion.html en/projects/contagion.html assets/style.css
git commit  # "L'explorateur de seuil dans les deux pages, calcul partage avec les tests node"
```

---

### Task 14: la prose définitive, verrouillée par les tests

Remplacer tous les premiers jets `⟨…⟩` par la prose finale, dans la voix du site
(spec §8 : constat, retournement, mécanisme avec dérivation sous `<details>`, correction,
ce qui reste, liste d'honnêteté à six points de la spec §9). Chaque nombre cité vient
d'un artefact calculé, puis les tests verrouillent la cohérence.

**Files:**
- Modify: `projets/contagion.html`, `en/projects/contagion.html`
- Test: `tools/contagion/tests/test_prose.py`

- [ ] **Step 1: Écrire les tests de prose (échouent tant que les ⟨…⟩ subsistent)**

```python
# tools/contagion/tests/test_prose.py
"""La prose tient les regles du site, et ses nombres sortent du calcul."""
import json
import pathlib
import re

import pytest

from tools.contagion.figures import PAGES, calculer, nombre

RACINE = pathlib.Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def pages():
    return {lang: chemin.read_text(encoding="utf-8") for lang, chemin in PAGES.items()}


def test_plus_aucun_premier_jet(pages):
    for lang, texte in pages.items():
        assert "⟨" not in texte and "⟩" not in texte, lang


def test_pas_de_tiret_cadratin(pages):
    for lang, texte in pages.items():
        assert "—" not in texte, lang


def test_espace_insecable_avant_les_unites(pages):
    for lang, texte in pages.items():
        corps = re.sub(r"<svg.*?</svg>", "", texte, flags=re.S)
        assert not re.search(r"\d %", corps), f"{lang}: espace secable avant %"


def test_la_correlation_pleine_periode_citee_est_la_bonne(pages):
    ctx = calculer()
    for lang, texte in pages.items():
        attendu = nombre(ctx["rho_pleine"], lang, 2)
        assert attendu in texte, f"{lang}: rho pleine periode {attendu} absent de la prose"


def test_le_noscript_cite_les_fixtures(pages):
    fixture = json.loads(
        (RACINE / "tools" / "js-tests" / "fixture-contagion.json").read_text())
    cas = next(c for c in fixture["cas"] if c["q"] == 0.9)
    for lang, texte in pages.items():
        for valeur in (cas["rho"], cas["rho_corrigee"]):
            assert nombre(valeur, lang, 2) in texte, (lang, valeur)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python3 -m pytest tools/contagion/tests/test_prose.py -q`
Expected: FAIL sur `test_plus_aucun_premier_jet` au moins.

- [ ] **Step 3: Écrire la prose FR puis EN**

Points imposés par la spec, à tenir dans la rédaction :

- §1 au premier degré, sans annoncer le retournement ; la procédure décrite en une
  phrase (déciles d'amplitude du rendement S&P, moyenne mobile 2 jours expliquée).
- §2 est le pivot : dire explicitement que le monde simulé a une corrélation constante
  **par construction**, et que la prédiction analytique passe dans les intervalles.
- §3 : la dérivation courte dans le texte (β ne bouge pas), la formule affichée, la
  dérivation complète sous `<details>` avec l'hypothèse d'homoscédasticité nommée.
- §5 : citer les moyennes par épisode du tableau de la figure 4, brute et corrigée, et
  dire ce que la correction n'efface pas.
- Liste d'honnêteté : les six points de la spec §9, ni plus ni moins.
- Un lien vers le papier (Forbes & Rigobon 2002, « No Contagion, Only Interdependence »,
  Journal of Finance) et un vers `tools/contagion/` sur GitHub, comme la page éclipse
  renvoie vers son rapport de validation.

- [ ] **Step 4: Vérifier le passage complet**

Run: `python3 -m pytest tools/contagion/tests -q && node --test tools/js-tests/`
Expected: PASS, tout.

- [ ] **Step 5: Commit**

```bash
git add projets/contagion.html en/projects/contagion.html tools/contagion/tests/test_prose.py
git commit  # "Prose des deux pages contagion, chaque nombre verrouille par test"
```

---

### Task 15: images OG, entrées d'accueil, sitemap

**Files:**
- Create: `tools/contagion/og.py`
- Create: `assets/og/contagion.jpg`, `assets/og/contagion-en.jpg` (produits)
- Modify: `index.html`, `en/index.html`, `sitemap.xml`

- [ ] **Step 1: Écrire `og.py`**

```python
# tools/contagion/og.py
"""Les deux images OG (1200x630), rendues depuis le meme calcul que la figure 3.

Usage: source .venv/bin/activate && python3 -m tools.contagion.og

matplotlib ne sert qu'ici: les figures de la page restent du SVG a la main.
Fond et encres repris de la charte sombre du site.
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tools.contagion.figures import calculer

RACINE = pathlib.Path(__file__).resolve().parents[2]
PAPIER, ENCRE, SERIE_A, SERIE_B = "#141414", "#e8e4dc", "#8a8a8a", "#7aa87a"
TITRES = {"fr": ("La contagion, ou moins qu'on ne dit", "brute", "corrigée"),
          "en": ("Contagion, or less than advertised", "raw", "corrected")}


def main():
    ctx = calculer()
    x = list(range(1, 11))
    for lang, (titre, la, lb) in TITRES.items():
        fig, ax = plt.subplots(figsize=(12, 6.3), dpi=100)
        fig.patch.set_facecolor(PAPIER)
        ax.set_facecolor(PAPIER)
        bruts = [t["rho"] for t in ctx["tranches_reelles"]]
        corr = [t["rho_corrigee"] for t in ctx["tranches_reelles"]]
        ax.axhline(ctx["rho_pleine"], color=ENCRE, lw=0.8, alpha=0.4)
        ax.plot(x, bruts, "o-", color=SERIE_A, lw=2, ms=8, label=la)
        ax.plot(x, corr, "o-", color=SERIE_B, lw=2, ms=8, label=lb)
        ax.set_ylim(0, 1)
        ax.set_title(titre, color=ENCRE, fontsize=22, pad=18)
        ax.legend(facecolor=PAPIER, labelcolor=ENCRE, edgecolor="none", fontsize=14)
        ax.tick_params(colors=ENCRE)
        for cote in ax.spines.values():
            cote.set_color(ENCRE); cote.set_alpha(0.3)
        nom = "contagion.jpg" if lang == "fr" else "contagion-en.jpg"
        fig.savefig(RACINE / "assets" / "og" / nom, format="jpg",
                    facecolor=PAPIER, bbox_inches="tight")
        plt.close(fig)
        print(nom)


if __name__ == "__main__":
    main()
```

Run: `python3 -m tools.contagion.og` puis ouvrir les deux JPG pour contrôle visuel
(1200 × 630 environ après bbox, lisible en vignette).

- [ ] **Step 2: Entrée dans les deux pages d'accueil**

`index.html`, en tête de la liste `<ul class="items">` de la section `#projets` :

```html
      <li>
        <h3><a href="/projets/contagion.html">La contagion, ou moins qu'on ne dit</a></h3>
        <p>« Les corrélations montent quand ça va mal » : la preuve classique recalculée sur
        S&amp;P 500 × CAC 40, reproduite à l'identique dans un monde simulé où rien ne bouge,
        puis corrigée du biais de Forbes-Rigobon.</p>
        <p class="more"><a href="/projets/contagion.html">lire →</a></p>
      </li>
```

`en/index.html`, même position dans `#projects` :

```html
      <li>
        <h3><a href="/en/projects/contagion.html">Contagion, or less than advertised</a></h3>
        <p>"Correlations rise in bad times": the classic evidence recomputed on the
        S&amp;P 500 × CAC 40 pair, reproduced identically in a simulated world where nothing
        moves, then corrected for the Forbes-Rigobon bias.</p>
        <p class="more"><a href="/en/projects/contagion.html">read →</a></p>
      </li>
```

- [ ] **Step 3: `sitemap.xml`**

Ajouter les deux `<url>` (`/projets/contagion.html`, `/en/projects/contagion.html`) sur le
modèle exact des entrées eclipse existantes, hreflang croisés compris, `lastmod` à la date
de publication.

- [ ] **Step 4: Vérifier**

Run: `python3 -m pytest tools/contagion/tests -q` — toujours PASS.
Run: `xmllint --noout sitemap.xml` (ou à défaut `python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse('sitemap.xml')"`).

- [ ] **Step 5: Commit**

```bash
git add tools/contagion/og.py assets/og/contagion.jpg assets/og/contagion-en.jpg \
        index.html en/index.html sitemap.xml
git commit  # "Images OG, entrees d'accueil et sitemap pour la page contagion"
```

---

### Task 16: passe finale — thèmes, mobile, budget, vérifications consignées

**Files:**
- Modify: au besoin seulement (`assets/style.css`, pages)

- [ ] **Step 1: La suite complète une dernière fois**

Run: `python3 -m pytest tools/contagion/tests tools/eclipse/tests -q && node --test tools/js-tests/`
Expected: PASS, tout, y compris les tests éclipse (aucune régression sur `style.css`).

- [ ] **Step 2: Vérifications manuelles, dans le navigateur (Chrome DevTools MCP)**

Sur `http://localhost:8777/projets/contagion.html` et la page EN :

- thème clair et thème sombre : figures lisibles, intervalles visibles, épisodes surlignés
  perceptibles dans les deux ;
- 320 px, 768 px, 1200 px : aucune barre de défilement horizontale de page, tableaux
  `<details>` contenus ;
- clavier seul : curseur de l'explorateur atteignable et pilotable, focus visible ;
- JavaScript coupé : bloc explorateur absent, `noscript` affiché, page complète par
  ailleurs ;
- les quatre figures et l'explorateur cohérents entre eux (même ρ pleine période affiché).

Consigner le résultat dans le message du commit final.

- [ ] **Step 3: Mesurer le budget**

```bash
gzip -c assets/data/contagion.json | wc -c
cat assets/js/contagion/*.js | gzip -c | wc -c
```

Attendu : JSON ≲ 70 Ko gzippé, JS ≲ 3 Ko gzippé. Reporter les valeurs mesurées dans le
message de commit (le budget spec §12 porte sur le JSON non compressé, < 200 Ko, déjà
testé par `test_budget_de_taille`).

- [ ] **Step 4: Relire les deux pages en entier**

Relecture éditoriale complète FR puis EN : tournures, cohérence des temps, la règle « pas
un seul tiret cadratin », les liens (papier F-R, GitHub, retour aux projets, bascule
fr/en des deux côtés).

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit  # "Page contagion en ligne: verifications des deux themes, mobile, sans JS, budgets mesures"
```

---

## Auto-revue du plan (faite à l'écriture)

- **Couverture de la spec** : §3 → tâche 2 ; §4.1-4.2 → tâches 1 et 3 ; §4.3 → tâche 7 ;
  §5 figures 1-4 → tâches 9-11 ; §6 → tâches 8 et 13 ; §7 → structure des tâches 1-12 ;
  §8 → tâches 12 et 14 ; §9 → tâche 14 ; §10 → tests de chaque tâche + tâche 16 ;
  §11 → tâche 15 ; §12 risques → tâche 1 en premier, test de budget en tâche 7, quintiles
  de repli mentionnés dans la spec seulement si la figure 1 l'exige.
- **Cohérence des signatures** : `correlation` (simulate.py) réutilisée par deciles,
  rolling, export, figures ; `delta_relatif`/`correction` (bias.py) partout ; conventions
  numériques (diviseur n, seuil `floor(q·n)`, garde `>=`) identiques en Python (export)
  et JS (explorer) — c'est l'objet des fixtures.
- **Les `⟨…⟩` des tâches 12-14 ne sont pas des placeholders du plan** : ce sont les
  nombres que la règle du site interdit de saisir à la main ; ils sont remplacés par les
  valeurs calculées à la tâche 14 et verrouillés par `test_prose.py`.
