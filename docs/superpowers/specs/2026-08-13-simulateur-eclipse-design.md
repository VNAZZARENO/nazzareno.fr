# Simulateur d'éclipse — éclipse totale du 12 août 2026

Spec de conception — 13 août 2026

## 1. Objectif

Une page projet qui restitue l'éclipse totale de Soleil du 12 août 2026 telle qu'elle a été
vue depuis trois lieux, avec une géométrie calculée à partir des éphémérides JPL et un ciel
rendu par un modèle de diffusion atmosphérique.

Le critère de réussite tient en une phrase : **un lecteur qui connaît le sujet doit pouvoir
vérifier les chiffres, et un lecteur qui ne le connaît pas doit avoir envie de rester.** Les
deux exigences se contraignent l'une l'autre — c'est le sujet de la §6.

Trois qualités, dans cet ordre de priorité en cas de conflit :

1. **Vrai** — la géométrie et les instants de contact sont calculés, pas ajustés à l'œil.
2. **Beau** — le rendu doit tenir comme image, pas seulement comme démonstration.
3. **Optimisé** — la page ne doit pas coûter plus cher qu'un article du site au repos.

## 2. Périmètre

### Dans le périmètre

- Une éclipse : celle du 12 août 2026.
- Trois lieux présélectionnés (§7), **affichés deux à la fois, côte à côte, au même instant**.
- Une frise de temps unique, commune aux deux panneaux, couvrant C1 → C4, en lecture
  automatique ou en pilotage manuel.
- Par panneau : le ciel depuis le sol, avec balayage horizontal du regard.
- Par panneau : un encart téléobjectif des deux disques à leur taille angulaire réelle.
- Version française et version anglaise.
- Dégradation complète sans JavaScript et sans WebGL2.

### Hors périmètre

Explicitement écartés, chacun défendable plus tard, aucun nécessaire ici :

- Carte de la bande de totalité.
- Saisie libre d'un lieu (latitude/longitude).
- Choix d'une autre éclipse, ou d'une date arbitraire.
- Profil du limbe lunaire issu des relevés LRO / Kaguya.
- Son, partage d'état par URL, export d'image.

## 3. Architecture

Trois étages, séparés par des interfaces étroites. Le navigateur ne calcule aucune éphéméride.

```
tools/eclipse/compute.py        →  assets/data/eclipse-2026-08-12.json  →  assets/js/eclipse/*
   (Python, hors ligne,             (chronologie échantillonnée,            (interpolation,
    skyfield + DE440s)               ~40 Ko avant compression)               LUT, rendu WebGL2)
```

Ce découpage est le choix structurant. Il permet de valider les chiffres une fois pour toutes
avec des outils d'astronomie sérieux, et laisse au runtime un travail trivial : interpoler une
table et dessiner. Il évite aussi d'embarquer un moteur d'éphémérides dans la page.

### 3.1 Étage hors ligne — `tools/eclipse/compute.py`

Dépendances : `skyfield`, éphéméride JPL **DE440s**, catalogue **Hipparcos** (chargé par
skyfield). Environnement local `.venv`, invoqué par `source .venv/bin/activate && python3 …`.
Le `.venv` et le `.bsp` ne sont pas versionnés ; le script et sa sortie le sont.

Pour chaque lieu, position **topocentrique** (`wgs84.latlon(lat, lon, elevation_m)`), pas de
**20 s** sur la fenêtre `C1 − 5 min → C4 + 5 min`. Le script produit à chaque pas :

- azimut et altitude apparents du Soleil et de la Lune, réfraction comprise
  (`altaz(temperature_C, pressure_mbar)`) ;
- rayons angulaires apparents des deux astres, déduits des distances topocentriques
  (R☉ = 695 700 km, R☾ = 1 737,4 km) — c'est ce qui décide totale contre annulaire ;
- séparation angulaire et angle de position ;
- magnitude `(r☉ + r☾ − d) / (2 r☉)` et obscuration (aire d'intersection de deux disques) ;
- **la fraction de flux solaire visible, par canal RGB** (§4.1) ;
- distances topocentriques du Soleil et de la Lune, nécessaires à la parallaxe du §4.2.

Les **instants de contact** sont obtenus par recherche de racine (Brent) sur `d(t)` :
C1 et C4 quand `d = r☉ + r☾`, C2 et C3 quand `d = |r☉ − r☾|`. C2 et C3 n'existent que si la
totalité a lieu au lieu considéré.

Les **astres visibles pendant la totalité** sont calculés au même endroit : planètes depuis
DE440s, étoiles depuis Hipparcos filtrées à `Vmag < 3.0`, converties en azimut/altitude à
l'instant du maximum. Si le catalogue Hipparcos n'est pas joignable, le script se rabat sur les
seules planètes et l'écrit dans son rapport.

### 3.2 Interface — `assets/data/eclipse-2026-08-12.json`

Un seul fichier, structure plate, valeurs arrondies à la précision utile (angles au
millième de degré, fractions à 1e-5) pour rester compact :

```jsonc
{
  "eclipse": { "id": "2026-08-12", "label": "...", "greatest_utc": "..." },
  "source":  { "ephemeris": "DE440s", "software": "skyfield x.y", "generated_utc": "..." },
  "sites": [{
    "id": "reykjavik",
    "name_fr": "...", "name_en": "...",
    "lat": ..., "lon": ..., "elevation_m": ..., "tz": "Atlantic/Reykjavik",
    "contacts": { "c1": "...", "c2": "...", "c3": "...", "c4": "..." },   // c2/c3 nullables
    "t0_utc": "...", "step_s": 20,
    "frames": [[sun_az, sun_alt, moon_az, moon_alt, r_sun, r_moon,
                mag, obsc, f_r, f_g, f_b, d_sun_km, d_moon_km], ...],
    "sky_at_max": { "planets": [...], "stars": [...] }
  }]
}
```

Les images sont des tableaux de nombres, pas des objets : c'est ce qui garde le fichier sous
les ~40 Ko pour trois lieux. Le contrat entre les deux étages est ce schéma, rien d'autre.

### 3.3 Étage navigateur — `assets/js/eclipse/`

Modules ES natifs, servis tels quels par GitHub Pages, aucun bundler, aucune dépendance tierce.
Sept fichiers, une responsabilité chacun :

| Fichier | Rôle | Dépend de |
|---|---|---|
| `gl.js` | outillage WebGL2 minimal : compilation, quad, textures, FBO | — |
| `data.js` | chargement du JSON, interpolation de l'état à l'instant `t` | — |
| `luts.js` | construction des trois LUT (§4.3) | `gl.js` |
| `sky.js` | passe ciel : shader, uniformes, dessin | `gl.js`, `luts.js` |
| `inset.js` | passe téléobjectif : disques, couronne, grains | `gl.js` |
| `ui.js` | frise, lieux, balayage du regard, `aria-live`, clavier | `data.js` |
| `main.js` | câblage, boucle `rAF`, drapeau `dirty`, observateurs | tous |

Chaque module doit rester compréhensible isolément : `sky.js` ne sait pas ce qu'est une frise,
`data.js` ne sait pas ce qu'est WebGL.

**Un seul canvas, un seul contexte WebGL2.** Le ciel occupe le cadre entier ; l'encart est
dessiné ensuite dans un second `gl.viewport` + `gl.scissor`. Deux canvases signifieraient deux
contextes — coûteux, plafonnés par le navigateur, et sujets à désynchronisation.

## 4. Le modèle physique

### 4.1 L'assombrissement centre-bord, et l'adaptation de l'œil

Deux mécanismes distincts, qu'il ne faut surtout pas confondre — ils jouent en sens opposés.

**Le flux ne suit pas l'aire découverte — et il s'en écarte dans les deux sens.** Le centre du
disque solaire est nettement plus brillant que son bord, ce qui produit deux régimes opposés :

- **Au début de l'éclipse**, la Lune mord le disque par le *limbe*, sa partie la plus sombre.
  Elle retire donc moins de lumière que d'aire, et il reste **plus** que `1 − obscuration`.
- **En partielle profonde**, la Lune couvre le centre et ne laisse qu'un croissant au limbe.
  Il reste alors **moins** que `1 − obscuration`. À 90 % d'obscuration, le calcul donne 7,1 %
  de lumière résiduelle en vert, pas 10 %.

Le basculement se produit exactement quand le centre du Soleil passe sous le disque lunaire,
c'est-à-dire quand `d < r☾`, ce qui équivaut à une magnitude de 0,5 — soit environ 34 %
d'obscuration. Ce critère est exact, pas empirique, et c'est lui que le test d'invariant
emploie pour vérifier les deux régimes séparément.

**L'œil, lui, répond de façon logarithmique.** C'est cela, et non l'assombrissement centre-bord,
qui explique qu'une partielle à 90 % se vive comme une journée à peine voilée. Un facteur dix
sur le flux ne se lit pas comme un facteur dix sur la scène.

La conséquence pour le rendu est directe et figure au §4.5 : l'exposition doit être **fixe et
partagée** entre les deux panneaux. Une auto-exposition par panneau rattraperait la chute de
lumière de l'Espagne et détruirait précisément ce que la page cherche à montrer.

Loi retenue : **Hestroffer & Magnan (1998)**, `I(μ)/I(1) = μ^α(λ)`, évaluée à trois longueurs
d'onde représentatives des primaires sRGB (≈ 465, 532, 630 nm). L'intégration de la portion non
occultée se fait numériquement sur une grille polaire du disque solaire, dans le script Python,
et produit `f_r, f_g, f_b`. La dépendance en longueur d'onde n'est pas cosmétique : elle rend
compte du fait que la lumière du croissant résiduel n'a pas la même couleur que celle du disque
entier.

### 4.2 L'ombre lunaire dans l'atmosphère — le cœur du rendu

Une éclipse ne peut pas être rendue en atténuant simplement le soleil au niveau de
l'observateur. Sous l'ombre, la lumière du ciel vient d'**ailleurs** : de l'atmosphère située
en dehors de l'ombre, à des dizaines de kilomètres. C'est précisément ce qui produit l'anneau de
crépuscule sur 360° — la signature visuelle d'une totalité.

Il faut donc, pour **chaque échantillon du raymarch**, savoir quelle fraction du disque solaire
est visible *depuis ce point-là*. Formulation retenue, exacte au premier ordre et très bon
marché :

> Un déplacement `Δ` du point d'échantillonnage par rapport à l'observateur décale la direction
> apparente de la Lune de `−Δ⊥ / D☾`, et celle du Soleil de `−Δ⊥ / D☉`. Comme
> `D☾ ≈ 3,8·10⁵ km` et `D☉ ≈ 1,5·10⁸ km`, la séparation apparente au point `P` vaut
> `|(û☉ − û☾) + Δ⊥ · (1/D☾ − 1/D☉)|`.

Le cône d'ombre, sa largeur au sol d'une centaine de kilomètres et son inclinaison tombent de
cette seule expression, sans géométrie ad hoc. `D☉` et `D☾` viennent du JSON, donc des
éphémérides.

La séparation ainsi obtenue est convertie en fraction de flux par la **LUT flux-séparation**
(§4.3), construite avec la même intégrale d'assombrissement centre-bord que le §4.1. Observateur
et atmosphère utilisent donc rigoureusement le même modèle.

### 4.3 Diffusion atmosphérique

Modèle retenu : **diffusion simple raymarchée + terme de diffusion multiple approché**, dans la
lignée de Hillaire (2020). Justification en une ligne : la diffusion simple seule rend le ciel
presque noir sous l'ombre et ne produit pas l'anneau à 360°, c'est-à-dire qu'elle échoue
exactement là où la pièce doit convaincre. Un précalcul 4D à la Bruneton est écarté pour une
raison de fond : sa table suppose un Soleil **uniforme**, hypothèse qu'une ombre mobile viole.

Composantes :

- **Rayleigh** — `β = (5,802, 13,558, 33,100)·10⁻⁶ m⁻¹`, hauteur d'échelle 8 km.
- **Mie** — `β ≈ 3,996·10⁻⁶ m⁻¹`, hauteur d'échelle 1,2 km, `g = 0,8`.
- **Ozone** — absorption en profil triangulaire entre 10 et 40 km. Non négociable ici : c'est
  elle qui donne au crépuscule son bleu profond, et le sujet de la page est un crépuscule.

Trois LUT, construites une seule fois au chargement, en rendu vers texture :

| LUT | Taille | Paramètres |
|---|---|---|
| Transmittance | 256 × 64 | altitude, cosinus de l'angle zénithal de visée |
| Diffusion multiple | 32 × 32 | altitude, cosinus de l'angle zénithal solaire |
| Flux ↔ séparation | 256 × 32, RGB | séparation `d / r☉`, rapport des rayons `r☾ / r☉` |

Les trois LUT sont **indépendantes du lieu** et donc construites une seule fois pour les deux
panneaux. C'est la raison pour laquelle la table flux ↔ séparation est bidimensionnelle : le
rapport `r☾ / r☉` diffère d'un lieu à l'autre et au fil du temps, et une table 1D obligerait à
en reconstruire une par panneau.

**Approximation assumée** : la LUT de diffusion multiple suppose un Soleil uniforme. Sous
l'ombre, elle est modulée par une fraction de flux *moyennée sur le voisinage* plutôt que
ponctuelle. Concrètement, la fraction est évaluée par la formule du §4.2 en quatre points
décalés de ±50 km horizontalement autour de l'échantillon, et moyennée — la diffusion multiple
qui éclaire un point sous l'ombre vient d'une région de cet ordre de grandeur. C'est un
compromis délibéré, et il figure dans le contrat de vérité (§6).

### 4.4 Le cadre

**Deux panneaux côte à côte, une frise commune.** Le cadre est coupé en deux moitiés, chacune
montrant un lieu au même instant. C'est la démonstration centrale de la page : à la même
seconde, Paris est encore en plein jour pendant que l'Espagne est dans la totalité. La §4.1 y
devient évidente sans qu'on ait besoin de l'expliquer.

Chaque moitié porte son propre sélecteur de lieu parmi les trois. Appariement par défaut :
**Paris à gauche, Espagne à droite**. Le balayage du regard est *partagé* : un seul décalage
d'azimut, appliqué relativement à la direction du Soleil propre à chaque lieu, de sorte que les
deux vues restent comparables. Sous 48 rem, les panneaux s'empilent verticalement.

Le coût en pixels est celui d'une vue unique, puisque chaque panneau occupe la moitié de la
largeur. Deux appels de dessin au lieu d'un, mais les trois LUT sont partagées.

**Vue ciel.** Caméra au sol, champ large (~120°) en projection équidistante : l'azimut est
appliqué linéairement à l'abscisse et l'altitude linéairement à l'ordonnée. L'horizon reste donc
une droite et les bords ne s'étirent pas, contrairement à une rectilinéaire à ce champ. Le
regard se balaie horizontalement
(glissement à la souris ou au doigt, **flèches gauche/droite au clavier**) — c'est ce qui rend
l'anneau de crépuscule à 360° découvrable plutôt que seulement affirmé. Sol : plan analytique,
albédo ≈ 0,1, éclairé par le soleil direct pondéré par la fraction de flux, plus l'irradiance du
ciel, avec perspective aérienne vers l'horizon. Volontairement abstrait : le sujet est le ciel.

**Encart téléobjectif.** Champ ≈ 1,5°. Disque solaire avec assombrissement centre-bord, disque
lunaire opaque à sa taille angulaire réelle, couronne, grains de Baily et anneau de diamant aux
abords de C2 et C3. Position dans le cadre : en bas à droite, sur un fond neutre discret, avec
un liseré d'un pixel. Sur mobile, il passe sous la vue ciel plutôt que par-dessus.

### 4.5 Exposition et courbe de rendu

Le calcul produit des luminances physiques, qui couvrent ici plus de quatre ordres de grandeur
entre le plein jour parisien et la totalité espagnole. Il faut donc une courbe de rendu, et le
choix de cette courbe est un choix de véracité autant que d'esthétique.

- **Exposition fixe**, calibrée une fois pour que le plein jour soit correctement exposé.
  Aucune auto-exposition, aucune adaptation temporelle.
- **Exposition identique dans les deux panneaux**, et inchangée quand on change de lieu ou
  d'instant. C'est la condition pour que la comparaison veuille dire quelque chose : deux
  images à la même exposition sont comparables, deux images auto-exposées ne le sont pas.
- **Courbe filmique** à pied doux, appliquée après l'exposition. Sa compression des hautes
  lumières et sa remontée des basses jouent le rôle de l'adaptation logarithmique décrite au
  §4.1 — ce qui est justement pourquoi Paris doit rester lumineux à l'écran sans qu'on triche
  sur les valeurs sous-jacentes.

Ce point est mentionné dans le contrat de vérité : ce qu'on voit n'est pas la luminance brute,
c'est une luminance physique passée dans une courbe fixe et annoncée.

### 4.6 Le disque et la couronne, dans l'encart

**Couronne.** Profil radial empirique de van de Hulst / Baumbach,
`B(r)/B☉ ≈ 10⁻⁶ (0,0532 r⁻²·⁵ + 1,425 r⁻⁷ + 2,565 r⁻¹⁷)`, `r` en rayons solaires, modulé par des
streamers procéduraux. Son intensité monte et descend avec la fraction de flux, donc elle
n'apparaît qu'au bon moment. Ce n'est **pas** une observation (§6).

## 5. Performance

Objectif : au repos, la page ne doit rien coûter de plus qu'un article du site.

- **Drapeau `dirty`** : aucune image n'est rendue tant que rien ne change. Frise à l'arrêt et
  regard immobile ⇒ zéro appel de dessin, zéro CPU. C'est le levier principal, avant toute
  optimisation de shader.
- **Résolution de rendu** à `0,7 × devicePixelRatio`, plafonnée à 1,5, remontée à l'échelle par
  le canvas.
- **Raymarch court** : 32 pas primaires, pas répartis non linéairement (plus serrés près de
  l'observateur), adossés à la LUT de transmittance — donc aucun raymarch secondaire vers le
  Soleil.
- **`IntersectionObserver`** : mise en pause hors écran. **`document.hidden`** : mise en pause
  onglet inactif.
- **`prefers-reduced-motion`** : pas de lecture automatique, une image rendue par changement de
  la frise, aucune animation continue.
- **Budget** : JSON + JS + shaders ≈ 60–90 Ko compressés. Aucune requête vers un tiers, aucun
  script externe, cohérent avec le reste du site.

Point de vigilance : au nord de l'Espagne le Soleil est très bas, donc les chemins optiques sont
longs et rasants. La répartition non linéaire des pas doit être vérifiée sur ce cas précis, qui
est le plus exigeant des trois.

## 6. Le contrat de vérité

Une section de la page, rédigée en clair, qui range chaque élément dans l'une des trois
catégories. Le site affirme ailleurs « aucune donnée inventée » : il faut donc dire franchement
ce qui relève du modèle. C'est aussi ce qui rend la page intéressante à lire.

**Calculé** (éphémérides JPL DE440s, vérifiable)
: positions et diamètres apparents du Soleil et de la Lune, instants de contact, magnitude,
obscuration, altitude solaire, planètes et étoiles visibles pendant la totalité.

**Modélisé d'après la physique** (lois publiées, pas d'ajustement à l'œil)
: assombrissement centre-bord, diffusion Rayleigh, Mie et absorption par l'ozone, luminance du
ciel, géométrie du cône d'ombre. Y compris l'approximation de voisinage du §4.3, nommée.

**Transformé pour l'affichage** (et donc à déclarer)
: l'exposition et la courbe filmique du §4.5. Ce qu'on voit n'est pas la luminance brute — mais
l'exposition est fixe et commune aux deux panneaux, ce qui garantit que la comparaison reste
honnête.

**Stylisé, et annoncé comme tel**
: la couronne — profil radial empirique et streamers procéduraux, pas une observation ; les
grains de Baily — l'*instant* est vrai, le motif ne l'est pas, faute de profil du limbe lunaire ;
l'horizon, délibérément abstrait.

## 7. Les trois lieux

Trois lieux disponibles, deux affichés à la fois.

1. **Paris** — partielle profonde. Le jour tient bon malgré une occultation massive : c'est la
   moitié gauche par défaut, et la démonstration visuelle du §4.1.
2. **Palma de Majorque** — totalité au ras de l'horizon, la signature de cette éclipse-là :
   Soleil à 2,6° d'altitude, totalité de 1 min 36 s, magnitude 1,015. Moitié droite par défaut.
   Retenue parmi huit candidates espagnoles sur le critère de l'altitude solaire la plus basse
   assortie d'une totalité franche — Valence descend aussi sous 5°, mais sa totalité d'une
   minute la place trop près de la limite de la bande.
3. **Reykjavík** — totalité avec le Soleil à bonne hauteur, sélectionnable dans l'un ou l'autre
   panneau. Il n'ajoute rien à la démonstration, mais c'est le seul des trois où l'anneau de
   crépuscule à 360° est pleinement lisible : en Espagne le Soleil frise l'horizon, et l'anneau
   se confond en partie avec le crépuscule ordinaire.

Le couple **Paris | Espagne** est l'état par défaut au chargement, et celui que rend le poster
de repli.

Aucun chiffre de magnitude, de durée ou d'altitude n'est écrit à la main dans les pages : tous
sont repris du JSON produit par le calcul.

## 8. Accessibilité et dégradation

- La frise est un `<input type="range">` natif : clavier fonctionnel sans code supplémentaire.
- Le balayage du regard est atteignable au clavier (flèches gauche/droite quand le canvas a le
  focus), avec un `:focus-visible` explicite.
- Les sélecteurs de lieu sont des `<select>` natifs, un par panneau, chacun étiqueté par le nom
  du panneau (« lieu de gauche », « lieu de droite »).
- Un `<output>` en `aria-live="polite"` **par panneau** annonce heure locale, altitude solaire,
  magnitude et obscuration, à une cadence limitée pour ne pas noyer un lecteur d'écran. C'est
  aussi ce qui rend la comparaison accessible sans voir l'image : les deux valeurs sont
  énoncées au même instant.
- Le canvas porte un `aria-label` décrivant la scène et son état.
- **Sans WebGL2, ou sans JavaScript** : une image poster **et** le tableau chiffré des contacts
  pour les trois lieux. Le poster est produit par le simulateur lui-même — une route `?poster=1`
  rend l'instant du maximum en pleine résolution et déclenche un export depuis le canvas, ensuite
  converti en WebP. Il ne s'agit donc pas d'une illustration séparée à maintenir en parallèle. La page reste entièrement lisible
  et utile — le simulateur est un supplément, jamais le seul porteur de l'information.
- Aucune information portée par la seule couleur, conformément à la ligne déjà tenue sur le site.
- Contrastes des contrôles vérifiés dans les deux thèmes, clair et sombre.

## 9. Intégration éditoriale

Fichiers créés :

- `projets/eclipse.html`, `en/projects/eclipse.html`
- `assets/js/eclipse/` (sept modules, §3.3)
- `assets/data/eclipse-2026-08-12.json`
- `assets/img/eclipse-poster-*.webp` (repli), `assets/og/eclipse.jpg`, `assets/og/eclipse-en.jpg`
- `tools/eclipse/compute.py`, `tools/eclipse/validate.py`, `tools/eclipse/requirements.txt`,
  `tools/eclipse/VALIDATION.md`

Fichiers modifiés :

- `index.html`, `en/index.html` — entrée dans la liste Projets
- `sitemap.xml` — les deux URL
- `assets/style.css` — styles du simulateur, dans la charte existante
- `.gitignore` — `.venv/`, `*.bsp`

Le texte de la page suit la voix du site : ce qui est calculé, ce qui est approximé, et pourquoi.
Il s'appuie sur la même idée que la page « données en image » — la structure se suffit à
elle-même, on ne l'embellit pas après coup.

## 10. Validation

Le site n'a pas de chaîne de test, et ce n'est pas ce projet qui doit en introduire une. La
validation porte donc là où elle a du sens : sur les chiffres.

- **`tools/eclipse/validate.py`** compare les contacts et magnitudes calculés aux valeurs
  publiées (NASA GSFC, EclipseWise, IMCCE, timeanddate) pour cette éclipse, avec des tolérances
  explicites (contacts < 30 s, magnitude < 0,005), et écrit le tableau comparatif dans
  `VALIDATION.md`. Le rapport est versionné : l'affirmation « vrai » devient vérifiable.

  La tolérance de 30 s n'est pas de la complaisance : les sources publiées divergent **entre
  elles** de 5 à 6 s sur les contacts et de 9 s sur l'instant du maximum, notamment parce que
  le ΔT supposé varie de 69,6 à 75,4 s. Serrer à 5 s reviendrait à mesurer ce désaccord plutôt
  que notre justesse. Une erreur réelle de la chaîne se compte en minutes, pas en secondes.
- **Invariants** vérifiés sur les données réellement produites : fraction de flux = 1 hors de
  [C1, C4] ; fraction nulle entre C2 et C3 aux lieux en totalité ; cohérence de la magnitude et
  de l'obscuration ; et surtout les **deux régimes** de l'assombrissement centre-bord du §4.1,
  vérifiés séparément de part et d'autre de la magnitude 0,5.

- **Un piège de réfraction, découvert au calcul.** skyfield annule la réfraction sous −1° de
  hauteur vraie. Le Soleil franchit ce seuil une vingtaine de secondes avant la Lune : pendant
  ces secondes, l'un est réfracté et l'autre non, et la séparation des deux disques bondit de
  0,55°, davantage que la somme de leurs rayons. À Palma, où C4 tombe une demi-heure après le
  coucher du Soleil, l'artefact tombait en pleine phase partielle et produisait une image de
  Soleil intact. Les deux astres sont donc soulevés du **même** angle, celui du Soleil : la
  réfraction ne doit pas toucher la géométrie relative, seule la hauteur apparente. Les astres
  du ciel, eux, sont éloignés les uns des autres et reçoivent chacun la leur.
- **Surcouche `?debug=1`** dans la page : images par seconde, nombre d'appels de dessin, valeurs
  courantes. Sert aussi bien au réglage visuel qu'à la vérification de la §5.
- **Vérifications manuelles** consignées : les deux thèmes, mobile et bureau, sans JavaScript,
  sans WebGL2, `prefers-reduced-motion` actif, parcours clavier complet.

## 11. Risques

| Risque | Portée | Traitement |
|---|---|---|
| Le shader atmosphérique demande plusieurs itérations avant d'être beau | Élevée — c'est la partie imprévisible | Le construire en dernier, sur une chaîne de données déjà validée ; le `?debug=1` et les LUT isolées permettent de régler sans tout relancer |
| Soleil très bas en Espagne : chemins rasants, précision du raymarch | Moyenne | Répartition non linéaire des pas, vérifiée d'abord sur ce cas |
| Catalogue Hipparcos indisponible au moment du calcul | Faible | Repli sur les seules planètes, mentionné dans le rapport |
| Le poster de repli doit être rendu par le shader, donc en dépend | Faible | Généré en fin de parcours, une fois le rendu figé |

Le reste de la chaîne — données, page, accessibilité, intégration — est prévisible. C'est le
rendu, et lui seul, qui porte l'incertitude.
