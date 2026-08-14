# La contagion, ou moins qu'on ne dit — corrélations conditionnelles et biais de Forbes-Rigobon

Spec de conception — 14 août 2026

## 1. Objectif

Une page projet qui démonte un graphe que tout le monde en gestion a déjà vu : la corrélation
entre marchés qui « monte vers 1 quand ça va mal ». La page recalcule ce graphe depuis les
cours quotidiens, montre qu'une simulation où la corrélation vraie est constante par
construction produit le même graphe, en donne le mécanisme (Forbes et Rigobon, 2002), applique
la correction, et regarde ce qui reste de 2008 et de mars 2020.

Le critère de réussite est le même que pour la page éclipse : **un lecteur qui connaît le
sujet doit pouvoir vérifier les chiffres, et un lecteur qui ne le connaît pas doit avoir envie
de rester.** S'y ajoute une contrainte propre au sujet : la page ne conclut pas « la contagion
n'existe pas ». Elle mesure la part d'artefact, et rapporte le reste tel qu'il sort du calcul,
quel qu'il soit.

Trois qualités, dans cet ordre en cas de conflit :

1. **Vrai** — chaque corrélation, chaque δ, chaque valeur de légende sort du calcul ; aucun
   nombre saisi à la main dans les pages.
2. **Dense** — l'argument tient en quatre figures ; tout ce qui n'y contribue pas est écarté.
3. **Léger** — figures SVG statiques, un explorateur en JavaScript sans dépendance, un JSON de
   données ; rien de chargé depuis un tiers.

## 2. Périmètre

### Dans le périmètre

- Un couple d'indices : **S&P 500 × CAC 40**, rendements quotidiens, historique maximal commun
  (CAC 40 disponible depuis le début des années 1990).
- Le biais d'échantillonnage des corrélations conditionnelles : dérivation, simulation,
  correction de Forbes-Rigobon, application aux données réelles.
- Quatre figures statiques calculées (§5) et un explorateur interactif (§6).
- Version française et version anglaise.
- Dégradation complète sans JavaScript : les figures statiques portent tout l'argument,
  l'explorateur est un supplément.

### Hors périmètre

Explicitement écartés, chacun défendable dans un billet suivant, aucun nécessaire ici :

- DCC-GARCH et toute corrélation conditionnelle paramétrique.
- Copules, dépendance de queue, coefficients de queue.
- Corrélations implicites d'options (indices de corrélation CBOE).
- Autres couples de marchés, choix interactif du marché source.
- Rafraîchissement périodique des données : le jeu est gelé à la date de téléchargement.

## 3. Le modèle et la formule

Tout repose sur un résultat élémentaire et son inversion.

Soit `y = α + βx + ε`, avec `ε` indépendant de `x` et de variance constante. On conditionne
sur un événement `A` défini sur `x` seul (par exemple : « |x| dépasse tel quantile »). Alors :

- `β` ne bouge pas : `Cov(x, y | A) = β · Var(x | A)` ;
- seule la part de variance de `y` expliquée par `x` change, donc la corrélation change :

```
ρ_A = ρ · √(1 + δ) / √(1 + δ·ρ²)        où δ = Var(x | A) / Var(x) − 1
```

- l'inversion, qui est la correction de Forbes-Rigobon :

```
ρ = ρ_A / √(1 + δ·(1 − ρ_A²))
```

Conditionner sur les jours agités (`δ > 0`) fait donc monter la corrélation d'échantillon
**sans qu'aucun paramètre structurel n'ait bougé**. La corrélation n'est pas un paramètre de
couplage : elle mélange le couplage (`β`) et le rapport signal sur bruit, et c'est le second
qui monte les jours de tempête.

**Choix de la variable de conditionnement : `|x|` contemporain**, c'est-à-dire l'amplitude du
rendement S&P du jour même, et non une volatilité glissante. C'est la version pure du biais de
sélection : elle opère même dans un monde i.i.d. sans mémoire, ce qui est exactement ce que la
figure 2 doit montrer. Le conditionnement sur volatilité glissante, plus proche des usages de
place, n'induit le biais que par la persistance de la volatilité ; il est traité par la
figure 4 (fenêtres glissantes) et discuté dans la liste d'honnêteté.

Les hypothèses de la formule — pas de variable omise, `ε` homoscédastique — sont fausses en
pratique, et la page le dit : c'est l'objet du §5, figure 4, et de la liste d'honnêteté (§9).

## 4. Données

### 4.1 Source et gel

CSV quotidiens **Stooq** (stooq.com), S&P 500 (`^spx`) et CAC 40 (symbole à confirmer à
l'implémentation, `^cac` attendu). Téléchargés une fois par `tools/contagion/data.py`, gelés
dans `tools/contagion/data/` avec, dans un fichier de manifeste : URL exactes, date et heure
de téléchargement, sommes SHA-256. La page ne charge rien depuis un tiers ; le dépôt contient
tout ce qu'il faut pour rejouer le calcul.

Si la profondeur d'historique du CAC 40 chez Stooq s'avère insuffisante (moins de ~25 ans),
repli documenté : autre miroir des mêmes cours, ou autre indice européen à historique long,
au prix d'une reformulation du couple. Ce risque est traité en premier (§11).

### 4.2 Rendements et synchronisation

Paris ferme à 17 h 30, New York à 22 h, heure de Paris : les rendements du même jour
calendaire ne se recouvrent que partiellement, et ce seul décalage fabrique de la corrélation
retardée. On suit Forbes et Rigobon eux-mêmes : **rendements logarithmiques en moyenne mobile
2 jours**, calculés sur le calendrier propre de chaque marché, puis appariés sur
l'intersection des dates. Le même calcul en jour calendaire simple figure dans les tableaux
`<details>` comme contrôle de robustesse ; l'autocorrélation MA(1) induite par la moyenne
mobile est déclarée dans la liste d'honnêteté.

### 4.3 Export vers la page

`assets/data/contagion.json` : les paires de rendements 2 jours arrondies à 6 décimales,
les dates, et un bloc de métadonnées (source, période, date de gel, n). De l'ordre de
9 000 lignes, ~150 Ko avant compression. C'est l'unique entrée de l'explorateur : il
recalcule tout, il n'affiche rien de précalculé (§6, parité).

## 5. Les quatre figures

Toutes statiques : SVG en ligne produits par `tools/contagion/figures.py` et injectés entre
repères dans les deux pages, exactement comme `tools/eclipse/figures.py`. En ligne et non en
`<img>` : c'est la seule forme qui hérite des variables CSS, donc qui existe dans les deux
schémas de couleur. Chaque figure porte sa vue tabulaire sous `<details>`, sans JavaScript.
Chaque nombre cité dans une légende est calculé et injecté, jamais saisi.

Sur les figures 1 à 3, chaque point de corrélation porte son **intervalle à 95 % par
bootstrap** (rééchantillonnage i.i.d. au sein du décile, B = 2 000, graine fixée). La liste
d'honnêteté précise que ce bootstrap ignore la dépendance sérielle et sous-estime donc un peu
la largeur des intervalles.

1. **Le constat** — corrélation S&P × CAC par décile de `|rendement S&P|`, la courbe qui
   monte. Axe des x : les déciles, étiquetés par l'amplitude médiane du décile en %. Droite
   horizontale : la corrélation pleine période. Écrite au premier degré : c'est le graphe qui
   « prouve » la contagion. Valeurs attendues, à mesurer : de ~0,2 au premier décile à ~0,8
   au dernier.
2. **Le retournement** — la même procédure appliquée à un monde simulé : couple gaussien
   i.i.d., corrélation vraie **constante** égale à la corrélation pleine période du couple
   réel, même taille d'échantillon. Trois tracés : les déciles Monte-Carlo (graine fixée),
   la prédiction analytique du §3 calculée avec le δ de chaque décile, la droite de la
   corrélation vraie. Monte-Carlo et analytique doivent se superposer ; la courbe monte comme
   la vraie. Le graphe-preuve est fabriqué à partir de rien.
3. **La correction** — les déciles réels de la figure 1, en gris, et les mêmes points passés
   par l'inversion de Forbes-Rigobon. Sous l'hypothèse nulle la courbe corrigée est plate à
   la corrélation pleine période ; l'écart maximal mesuré à cette droite est donné dans la
   légende. C'est la figure de l'argument, et celle dont sort l'image OG.
4. **Ce qui reste** — corrélation glissante 60 jours, brute et corrigée (δ pris sur la
   variance glissante du S&P rapportée à la variance pleine période), de 1991 à 2026, avec
   2008 et février-avril 2020 surlignés. La brute monte vers 0,9 dans les deux épisodes ; ce
   que la corrigée en conserve est le contenu réel du mot « contagion » — la page rapporte ce
   qui sort du calcul, y compris si la corrigée monte aussi.

## 6. L'explorateur

Un encart interactif après la figure 3, sur les données réelles. Un curseur — « garder les
jours où |rendement S&P| dépasse le quantile q », q de 0 à 0,95 — et quatre valeurs
recalculées à chaque position : n jours retenus, δ, corrélation brute du sous-échantillon,
corrélation corrigée. Deux barres contre la droite de référence pleine période : la brute
grimpe, la corrigée reste posée. Aucune animation continue, un rendu par mouvement du
curseur.

- **Modules** : `assets/js/contagion/explorer.js` (calcul pur : corrélation, δ, correction
  sur un sous-échantillon — aucun accès au DOM) et `assets/js/contagion/ui.js` (curseur,
  affichage, `aria-live`). Modules ES natifs, aucun bundler, aucune dépendance.
- **Parité JS/Python** : `tools/contagion/export.py` écrit des fixtures — pour
  q ∈ {0 ; 0,5 ; 0,9} au moins : n, δ, ρ brute, ρ corrigée — et un test dans
  `tools/js-tests/` exécute `explorer.js` sous node contre ces fixtures, égalité à 10⁻⁹
  relatif. Le lecteur et le pytest voient les mêmes nombres.
- **Accessibilité** : `<input type="range">` natif, un `<output>` en `aria-live="polite"` à
  cadence limitée, valeurs toujours présentes en texte, rien porté par la seule couleur.
- **Dégradation** : sans JavaScript, l'encart se réduit à un paragraphe qui dit ce que
  l'explorateur aurait montré ; les figures statiques portent déjà tout l'argument.

## 7. Le code

Miroir de `tools/eclipse/`, une responsabilité par fichier :

```
tools/contagion/
  data.py        # téléchargement Stooq, gel, manifeste avec sommes SHA-256
  returns.py     # rendements log par calendrier propre, moyenne mobile 2 jours, appariement
  bias.py        # la formule du §3 : conditionnelle, inversion, δ — fonctions pures
  simulate.py    # Monte-Carlo gaussien à graine fixée
  deciles.py     # découpage par déciles de |x|, corrélations, corrections, bootstrap
  rolling.py     # fenêtres glissantes 60 jours, δ glissant, épisodes surlignés
  figures.py     # les quatre SVG, injectés entre repères dans les deux pages
  export.py      # assets/data/contagion.json + fixtures de parité JS
  build.py       # orchestration, idempotent : deux exécutions ⇒ le même HTML
  tests/
assets/js/contagion/
  explorer.js    # calcul pur, importé par la page ET par le test node
  ui.js
```

Environnement : `.venv` local, `source .venv/bin/activate && python3 …`, dépendances numpy
et pandas dans `tools/contagion/requirements.txt`. Les CSV gelés et le JSON exporté sont
versionnés ; le `.venv` ne l'est pas.

## 8. Les pages

`projets/contagion.html` et `en/projects/contagion.html`, gabarit billet de la page éclipse :
`body class="article post"`, date en tête, mots-clés entre filets, h2 sans filet supérieur,
colonne à 46 rem, signature de fin. Titre de travail : **« La contagion, ou moins qu'on ne
dit »** ; anglais : **« Contagion, or less than advertised »**.

Structure :

1. **Chapo** — la phrase répétée en gestion, et l'annonce : ce graphe est recalculé ici
   depuis les cours quotidiens, et une bonne partie en est un artefact d'échantillonnage.
2. **§1 Le constat** — figure 1, au premier degré.
3. **§2 Le retournement** — figure 2. Le pivot de la page.
4. **§3 Le mécanisme** — la dérivation en trois lignes dans le texte (β ne bouge pas, le
   rapport signal sur bruit bouge), la formule, la dérivation complète sous `<details>`.
5. **§4 La correction** — l'inversion, figure 3, puis l'explorateur.
6. **§5 Ce qui reste** — figure 4, et la discussion honnête : ce que la correction suppose,
   ce qu'elle ne peut pas dire, ce qui subsiste dans les deux épisodes.
7. **Liste d'honnêteté** (§9), mots-clés, signature.

Le texte suit la voix du site : ce qui est calculé, ce qui est supposé, et pourquoi. Pas de
tiret cadratin, espaces insécables devant les unités, aucun nombre saisi à la main.

## 9. La liste d'honnêteté

Rédigée en clair dans la page, comme le contrat de vérité de la page éclipse :

- La correction suppose le choc venu du S&P ; conditionner sur le CAC donne d'autres
  chiffres, et ce choix est une hypothèse économique, pas une neutralité.
- Elle suppose `ε` homoscédastique et aucune variable omise — faux en pratique (chocs
  communs mondiaux, volatilité propre du CAC) ; le sens du biais résiduel est discuté.
- La moyenne mobile 2 jours, prise à Forbes et Rigobon, induit une autocorrélation MA(1) ;
  le calcul en jour simple figure en contrôle dans les tableaux.
- Le Monte-Carlo est gaussien : un monde plus sage que le vrai. Les queues épaisses rendent
  les corrélations des déciles extrêmes plus bruitées que le bootstrap i.i.d. ne le dit.
- Le conditionnement de place se fait sur volatilité glissante, pas sur `|x|` du jour ; la
  version retenue isole le mécanisme, la figure 4 couvre l'autre.
- Stooq est déclaratif ; cours de clôture, dividendes non réinvestis, corrélations de
  Pearson sur rendements logarithmiques.

## 10. Validation

Conformément au choix de cadrage : **la mécanique se valide seule**, contre la formule
analytique — pas d'ancre externe chiffrée pour la partie empirique. Pytest dans
`tools/contagion/tests/`, dans l'esprit des douze tests de la page éclipse : chaque
affirmation d'une légende est couverte par un test.

- **`bias.py`** : inversion ∘ conditionnelle = identité ; δ = 0 ⇒ ρ ; monotonie en δ ;
  limites δ → −1 (ρ_A → 0) et δ → ∞ (ρ_A → signe de ρ) ; symétrie en −ρ.
- **Monte-Carlo contre analytique** : à grand n (5·10⁵), corrélation conditionnelle par
  décile égale à la prédiction du §3 sous tolérance dimensionnée à l'erreur Monte-Carlo
  (3 écarts-types de l'estimateur) ; la correction retrouve la ρ vraie dans son intervalle.
- **Déciles réels** : la monotonie affirmée par la légende de la figure 1 (dernier décile
  au-dessus du premier de la marge annoncée) ; l'écart maximal de la courbe corrigée à la
  pleine période égal à celui de la légende de la figure 3.
- **`returns.py`** : appariement sans NaN, autocorrélation MA(1) présente et déclarée,
  robustesse jour simple contre 2 jours dans les bornes données par le tableau.
- **Parité JS/Python** : les fixtures du §6, à 10⁻⁹ relatif, exécutées sous node dans
  `tools/js-tests/`.
- **Prose** : espaces insécables devant % et pt, aucun tiret cadratin, chaque nombre de
  légende égal à la valeur recalculée ; injection entre repères idempotente.
- **Vérifications manuelles consignées** : deux thèmes, mobile et bureau, sans JavaScript,
  parcours clavier de l'explorateur, lecteur d'écran sur l'`aria-live`.

## 11. Intégration éditoriale

Fichiers créés :

- `projets/contagion.html`, `en/projects/contagion.html`
- `assets/js/contagion/explorer.js`, `assets/js/contagion/ui.js`
- `assets/data/contagion.json`
- `assets/og/contagion.jpg`, `assets/og/contagion-en.jpg` — rendus depuis la figure 3
- `tools/contagion/` complet (§7), CSV gelés et manifeste compris

Fichiers modifiés :

- `index.html`, `en/index.html` — entrée dans la liste Projets
- `sitemap.xml` — les deux URL
- `assets/style.css` — styles de l'explorateur, dans la charte existante

## 12. Risques

| Risque | Portée | Traitement |
|---|---|---|
| Historique CAC 40 chez Stooq court ou symbole absent | Moyenne — c'est la seule dépendance externe | Traité en tout premier : `data.py` et le manifeste avant toute autre tâche ; replis du §4.1 |
| La courbe corrigée n'est pas plate sur les données réelles | Nulle — ce n'est pas un échec | C'est le contenu du §5 « ce qui reste » ; la page rapporte le chiffre qui sort |
| Corrélations des déciles extrêmes bruitées, figure 1 peu lisible | Faible | Intervalles bootstrap dès la conception ; au pire, quintiles au lieu de déciles, dit dans la légende |
| Taille du JSON au-dessus de l'attendu | Faible | Arrondi à 6 décimales, dates compactées ; budget annoncé ~150 Ko avant compression, mesuré au build |

Le reste — formules, figures, pages, intégration — est prévisible : c'est la disponibilité
des données, et elle seule, qui porte l'incertitude, d'où son traitement en première tâche.
