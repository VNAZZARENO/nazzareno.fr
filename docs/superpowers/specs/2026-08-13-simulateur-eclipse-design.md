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
- Trois lieux, présélectionnés (§7).
- Une frise de temps couvrant C1 → C4, lecture automatique et pilotage manuel.
- Vue principale : le ciel depuis le sol, avec balayage horizontal du regard.
- Encart : vue téléobjectif des deux disques à leur taille angulaire réelle.
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

### 4.1 L'assombrissement centre-bord — le détail qui décide de tout

L'éclat du Soleil **n'est pas** proportionnel à la fraction de disque découverte : le centre du
disque est nettement plus brillant que le bord. C'est pour cette raison qu'à 90 % d'occultation
il fait encore presque jour, et que tout s'effondre dans les dernières secondes.

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
| Flux ↔ séparation | 256 × 1, RGB | séparation angulaire normalisée |

**Approximation assumée** : la LUT de diffusion multiple suppose un Soleil uniforme. Sous
l'ombre, elle est modulée par une fraction de flux *moyennée sur le voisinage* plutôt que
ponctuelle. Concrètement, la fraction est évaluée par la formule du §4.2 en quatre points
décalés de ±50 km horizontalement autour de l'échantillon, et moyennée — la diffusion multiple
qui éclaire un point sous l'ombre vient d'une région de cet ordre de grandeur. C'est un
compromis délibéré, et il figure dans le contrat de vérité (§6).

### 4.4 Le cadre

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

**Stylisé, et annoncé comme tel**
: la couronne — profil radial empirique et streamers procéduraux, pas une observation ; les
grains de Baily — l'*instant* est vrai, le motif ne l'est pas, faute de profil du limbe lunaire ;
l'horizon, délibérément abstrait.

## 7. Les trois lieux

Choisis pour couvrir trois régimes distincts :

1. **Reykjavík** — totalité, Soleil à une hauteur confortable. Le cas de référence.
2. **Un point du nord de l'Espagne** — totalité au ras de l'horizon, la signature de cette
   éclipse-là. Ville arrêtée après calcul, sur le critère d'une totalité franche à basse
   altitude solaire.
3. **Paris** — partielle profonde. Le cas pédagogique : le jour tient bon malgré une occultation
   massive, ce qui démontre visuellement le §4.1.

Aucun chiffre de magnitude, de durée ou d'altitude n'est écrit à la main dans les pages : tous
sont repris du JSON produit par le calcul.

## 8. Accessibilité et dégradation

- La frise est un `<input type="range">` natif : clavier fonctionnel sans code supplémentaire.
- Le balayage du regard est atteignable au clavier (flèches gauche/droite quand le canvas a le
  focus), avec un `:focus-visible` explicite.
- Un `<output>` en `aria-live="polite"` annonce heure locale, altitude solaire, magnitude et
  obscuration, à une cadence limitée pour ne pas noyer un lecteur d'écran.
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
  publiées par le NASA GSFC (Espenak) pour cette éclipse, avec des tolérances explicites
  (contacts < 5 s, magnitude < 0,002), et écrit le tableau comparatif dans `VALIDATION.md`.
  Le rapport est versionné : l'affirmation « vrai » devient vérifiable par un lecteur.
- **Invariants** vérifiés par le script : fraction de flux = 1 hors de [C1, C4] ; fraction nulle
  entre C2 et C3 aux lieux en totalité ; magnitude et obscuration monotones de part et d'autre
  du maximum ; continuité de l'interpolation aux bornes.
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
