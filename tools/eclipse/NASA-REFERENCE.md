# Valeurs publiees utilisees par le simulateur d'eclipse

Ce fichier recense les grandeurs que le simulateur ne calcule pas lui-meme mais
reprend d'une source publiee, avec la reference exacte et la date de
consultation. Toute valeur codee en dur dans `tools/eclipse/` doit apparaitre
ici.

## Assombrissement centre-bord

### Source

> A. Keith Pierce et Charles D. Slaughter, « Solar limb darkening. I:
> λλ(3033–7297) », *Solar Physics*, vol. 51, n° 1, 1977, p. 25–41.
> DOI [10.1007/BF00240442](https://doi.org/10.1007/BF00240442).
> Code bibliographique ADS `1977SoPh...51...25P`.

Fac-simile consulte le **13 aout 2026** :
<https://articles.adsabs.harvard.edu/pdf/1977SoPh...51...25P>
(notice : <https://ui.adsabs.harvard.edu/abs/1977SoPh...51...25P/abstract>).

Le fac-simile est une numerisation en mode image, sans couche de texte : les
tables ont donc ete relues a l'oeil sur un rendu a 600 dpi. A plus basse
resolution la 5e decimale se confond (un `8` se lit `4`) — qui rouvre ce
fichier pour verifier un chiffre doit rendre la page a 600 dpi, pas moins.

Observations faites au telescope solaire McMath du Kitt Peak National
Observatory, 14 journees entre mars 1974 et janvier 1975, corrigees de la
lumiere diffusee et du seeing. C'est le jeu de coefficients de reference pour
l'assombrissement centre-bord du Soleil dans le visible, celui que citent
Neckel & Labs (1994) et *Allen's Astrophysical Quantities* (Cox, 2000).

### Forme employee par l'article

L'article donne plusieurs representations. Celle qui nous interesse est sa
**Table III**, « Coefficients of 2nd degree, μ = cos θ, fit to the limb
darkening », qui tabule l'equation (10) de l'article :

    I(λ, μ) = A(2) + B(2) μ + C(2) μ²

C'est deja, au changement de variable pres, la loi quadratique. **Aucun ajustement
par moindres carres n'a ete refait de notre cote** : la conversion ci-dessous est
une simple identite algebrique.

### Conversion vers la loi quadratique

La loi quadratique usuelle s'ecrit

    I(μ)/I(1) = 1 - u1 (1-μ) - u2 (1-μ)²
              = (1 - u1 - u2) + (u1 + 2 u2) μ - u2 μ²

En identifiant terme a terme avec `A(2) + B(2) μ + C(2) μ²` :

    u1 = B(2) + 2 C(2)
    u2 = -C(2)

et reciproquement `A(2) = 1 - u1 - u2`, ce qui donne directement l'intensite au
limbe. La normalisation au centre est automatique puisque
`A(2) + B(2) + C(2) = 1` dans la table.

### Lignes retenues de la Table III

Critere de choix : pour chacune des trois cibles 610 / 550 / 470 nm, la longueur
d'onde tabulee la plus proche. Rien d'autre.

| canal | λ (Å) | λ (nm) | A(2) | B(2) | C(2) | u1 | u2 |
|---|---|---|---|---|---|---|---|
| rouge | 6109.75 | 610.975 | 0.34653 | 0.92982 | −0.27635 | **0.37712** | **0.27635** |
| vert  | 5522.00 | 552.200 | 0.29462 | 0.98032 | −0.27494 | **0.43044** | **0.27494** |
| bleu  | 4683.06 | 468.306 | 0.21495 | 0.99746 | −0.21241 | **0.57264** | **0.21241** |

Le bleu est le choix le moins bien cale des trois : la table est clairsemee
dans cette region, et 4683.06 Å ne l'emporte sur 4719.00 Å que de 0.2 nm.
Par ailleurs la primaire bleue sRGB a une longueur d'onde dominante plutot
voisine de 465 nm que de 470 nm ; sous ce critere-la c'est 4615.10 Å qui serait
la plus proche. Mais les trois lignes candidates donnent un limbe compris entre
0.21391 et 0.21495, soit un demi-pour-cent d'ecart relatif : l'arbitrage ne
change rien en pratique.

Les trois lignes retenues verifient `A + B + C = 1.00000` exactement, ce qui
sert de controle de transcription — utile sur un fac-simile de 1977. La ligne
5199.30 Å, elle, est manifestement corrompue a la numerisation : elle porte
`B(2) = 1.97674` et somme a 2.00000. Elle n'est pas utilisee ici.

Ce sont ces trois paires `(u1, u2)`, dans cet ordre (rouge, vert, bleu), qui
constituent `SRGB_LIMB_COEFFS` dans `tools/eclipse/limb.py`. Le miroir
JavaScript `assets/js/eclipse/flux.js` doit recopier ces memes valeurs.

### Controles de vraisemblance

Le rapport limbe/centre vaut `I(0) = 1 - u1 - u2 = A(2)` :

| canal | I(limbe)/I(centre) |
|---|---|
| rouge 610.975 nm | 0.34653 |
| vert  552.200 nm | 0.29462 |
| bleu  468.306 nm | 0.21495 |

- Ordre de grandeur attendu dans le visible, environ un tiers : verifie. Le vert
  ressort a 29.5 %, tout juste sous la fourchette 30–40 % souvent citee. Cette
  fourchette est une regle approximative : la valeur exacte depend de la
  longueur d'onde et de la forme d'ajustement retenue. La valeur au limbe est en
  effet la plus fragile de la courbe, car elle est une extrapolation a μ = 0 :
  les auteurs eux-memes ne considerent leurs observations fiables que jusqu'a
  μ = 0.1, projetables a μ = 0.05 « with some confidence ». Aux memes longueurs
  d'onde, l'ajustement du 5e degre (Table IV) extrapole un limbe plus sombre
  encore — 0.29397, 0.24092 et 0.20728 — soit une dispersion de quelques points
  entre representations. Le flux integre, lui, est domine par les regions ou les
  deux ajustements coincident, et est donc bien plus stable que I(0).
- Le limbe est **plus rouge** que le centre, l'assombrissement se creusant vers
  le bleu : 0.347 > 0.295 > 0.215. Verifie.

### Consequence sur le flux, pour memoire

C'est le point de la specification que l'on enonce le plus souvent a l'envers.
En partielle profonde la Lune couvre le centre du disque et ne laisse qu'un
croissant au limbe, la partie la plus sombre : le flux residuel tombe **sous**
la valeur naive `1 - obscuration`. Avec les coefficients ci-dessus, pour deux
disques de meme rayon :

| obscuration geometrique | `1 - obscuration` | flux reel (r, v, b) |
|---|---|---|
| 90 % | 0.100 | 0.0735, 0.0707, 0.0654 |
| 99 % | 0.010 | 0.0053, 0.0048, 0.0041 |

Une partielle a 90 % ne laisse donc pas 10 % de la lumiere, mais environ 7 %.
Si elle se vit malgre tout comme du plein jour, ce n'est pas a cause de
l'assombrissement centre-bord — qui va dans l'autre sens — mais de la reponse
approximativement logarithmique de l'oeil.

## Instants de contact publies

### Pourquoi cette section existe, et quand elle a ete ecrite

La page revendique une eclipse astronomiquement juste. Cette section est ce qui
rend la revendication verifiable : elle fige, **avant que notre propre chaine de
calcul n'ait produit le moindre chiffre**, les valeurs publiees contre lesquelles
elle sera confrontee.

Consequence de methode, a respecter si quelqu'un reprend ce fichier : **aucune
valeur ci-dessous n'a ete calculee ici.** Toutes sont recopiees d'une source
externe publiee, avec son URL et sa date de consultation. Rien ne vient de
`tools/eclipse/`. Confronter le code a des nombres qu'il aurait lui-meme produits
ne validerait rien du tout.

Toutes les consultations datent du **13 aout 2026**, soit le lendemain de
l'eclipse.

### Sources consultees

| clef | source | portee | URL |
|---|---|---|---|
| **GSFC** | Fred Espenak, NASA/GSFC, *Five Millennium Canon of Solar Eclipses*, page de donnees de l'eclipse | circonstances generales, elements besseliens | <https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl=20260812> |
| **GSFC-path** | idem, table du trajet de la ligne centrale | trajet, largeur, duree le long du trajet | <https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2026Aug12Tpath.html> |
| **EW** | Fred Espenak, *EclipseWise*, page principale de l'eclipse | circonstances generales, contacts de l'ombre | <https://www.eclipsewise.com/solar/SEprime/2001-2100/SE2026Aug12Tprime.html> |
| **IMCCE** | IMCCE / Observatoire de Paris, fiche « Éclipse totale du 12 août 2026 » (PDF) | circonstances generales | <https://promenade.imcce.fr/en/images/pdf/eclsol-12aout2026.pdf> |
| **IGN** | Instituto Geografico Nacional / Observatorio Astronomico Nacional (Espagne), fiche communale de Palma | circonstances locales espagnoles, coordonnees, altitude du terrain | <https://eclipses.ign.es/src/img/eclipse-26/infografia/07040_Palma_Illes_Balears.jpg> (depuis <https://eclipses.ign.es/eclipse-total-sol-de-12-de-agosto-2026.html>) |
| **T&D** | timeanddate.com, pages « eclipse in <ville> » | circonstances locales des trois villes | voir chaque ville ci-dessous |
| **IS-alm** | *Almanak Haskola Islands* (almanach de l'Universite d'Islande) | duree de la totalite a Reykjavik | <http://www.almanak.hi.is/myrk2200.html> |
| **IS-sol** | solmyrkvi2026.is, site islandais dedie a l'eclipse | contacts a Reykjavik, horaires de l'ombre sur l'Islande | <https://solmyrkvi2026.is/almyrkvi-a-solu-2026> |
| **WP-fr** | Wikipedia FR, table « Horaires de l'eclipse totale par localite », qui cite vigiacosmos.es et la NASA | recoupement tertiaire | <https://fr.wikipedia.org/wiki/%C3%89clipse_solaire_du_12_ao%C3%BBt_2026> |

Note de provenance : `www.eclipsewise.com` et `www.timeanddate.com` repondent 403
a une requete directe depuis cette machine. Leurs pages ont ete lues via le
proxy de lecture `r.jina.ai`, qui rend le texte de la page telle qu'un
navigateur la recoit. Le contenu est celui du site, mais quiconque veut
re-verifier depuis un navigateur ordinaire doit ouvrir les URL directes
ci-dessus, pas le proxy.

### Circonstances generales

| grandeur | GSFC | EW | IMCCE |
|---|---|---|---|
| maximum de l'eclipse, echelle dynamique | 17:47:06 TDT | 17:47:05.8 TD | — |
| **maximum de l'eclipse, UTC** | **17:45:51** | **17:45:53.3** (UT1) | **17:46:00** |
| latitude du maximum | 65.2° N | 65°13.4′ N | 65°11′41.1″ N |
| longitude du maximum | 25.2° W | 25°13.7′ W | 25°12′08.7″ W |
| duree centrale au maximum | 02m18s | 02m18.21s | — |
| duree centrale maximale | — | 02m18.23s a 17:44:41.5 UT1 | — |
| gamma | 0.8977 | — | — |
| magnitude de l'eclipse | 1.0386 | — | 1.03994 (« grandeur ») |
| largeur du trajet | 293.9 km | 294.0 km | — |
| hauteur du Soleil au maximum | 25.8° | 25.8° | — |
| azimut du Soleil au maximum | 248.4° | 248.4° | — |
| saros | 126 | — | — |
| ephemeride | VSOP87 / ELP2000-82 | JPL DE405 | non precisee |
| ΔT retenu | 75.4 s | 72.4 s | 75.319 s (UT1−TT = −75.319 s) |

**Valeurs de reference retenues** : instant du maximum **2026-08-12T17:45:51Z**
(GSFC), duree maximale de la totalite **2 min 18 s** (GSFC ; 02m18.21s en EW).

**Desaccords, a garder en tete pour l'etape de validation.** Les trois sources
ne donnent pas le meme instant en UTC : 17:45:51, 17:45:53.3 et 17:46:00, soit
neuf secondes d'amplitude — davantage que la tolerance de 5 s prevue pour la
comparaison des contacts. GSFC et EW sont pourtant du meme auteur : ils
different par l'ephemeride (VSOP87/ELP2000 contre DE405) et par le ΔT suppose
(75.4 s contre 72.4 s, soit 3.0 s d'ecart, pour 2.3 s d'ecart sur l'instant
publie en UTC). Il n'y a donc pas une valeur vraie et deux fausses : il y a
trois conventions.

Les magnitudes different aussi : 1.0386 (GSFC) contre 1.03994 (IMCCE). Un
millieme de magnitude, mais c'est un rappel que « magnitude » n'est pas une
mesure unique.

La fiche d'infobox de Wikipedia FR annonce, elle, un maximum a 17:45:43.7 pour
un gamma et une largeur de trajet identiques a ceux de GSFC. Cette valeur n'est
raccordee a aucune source sur la page et sort de la fourchette des trois autres ;
elle n'est pas retenue.

### Le trajet de la totalite

Faits releves, pas deduits :

- L'ombre touche la Terre a **16:58:05.6 UT1** par 74°56.0′ N, 117°35.5′ E
  (premier contact exterieur U1, EW) — cote nord de la Siberie, peninsule de
  Taimyr.
- Elle remonte vers le nord, passe pres du pole Nord, franchit l'ocean Arctique
  et le nord-est du Groenland. La table du trajet (GSFC-path) montre le Soleil a
  7° de hauteur a 17:02 UTC, 16° a 17:10 UTC.
- Le maximum a lieu au large des cotes nord-ouest de l'Islande (65°13′ N,
  25°14′ W).
- L'ombre traverse l'ouest de l'Islande : elle aborde le pays au phare de
  Straumsnes, sur les Hornstrandir, a **17:43:28 UTC**, balaie les fjords de
  l'Ouest, Snaefellsnes, Reykjavik et la peninsule de Reykjanes, et quitte
  l'Islande a Reykjanesta a **17:50:07 UTC**, soit 6 min 48 s au total (IS-sol).
- Traversee de l'Atlantique nord, puis arrivee sur l'Espagne a **18:25:44 UTC**
  (IS-sol) dans la soiree locale.
- L'ombre traverse le nord de l'Espagne d'ouest en est, de la Galice et des
  Asturies jusqu'a la Mediterranee, en passant par de nombreux chefs-lieux de
  province. Elle effleure un court segment de l'extreme nord-est du Portugal
  (Aveleda e Rio de Onor : 6 s de totalite, WP-fr).
- Elle finit au coucher du Soleil sur les Baleares et la Mediterranee. Dernier
  contact exterieur U4 a **18:34:05.3 UT1** par 37°47.6′ N, 4°32.6′ E (EW).
- Le reste de l'Europe, une partie de l'Amerique du Nord et le nord-ouest de
  l'Afrique voient une eclipse partielle.

La signature de cette eclipse en Espagne est la hauteur du Soleil : la table
GSFC-path donne, sur la ligne centrale, 14° a 18:24 UTC, 10° a 18:28 UTC, 8° a
18:30 UTC et **2° a 18:32 UTC**. La totalite s'y est jouee tres pres de
l'horizon.

### Choix de la ville espagnole : Palma de Majorque

Critere de la specification : une totalite franche, a la hauteur de Soleil la
plus basse possible. Valeurs relevees pour departager les huit candidates,
toutes tirees de T&D afin que la comparaison porte sur une seule methode ; la
duree est l'intervalle C2–C3 lu sur la page.

| ville | hauteur apparente du Soleil au maximum | duree de la totalite | magnitude |
|---|---|---|---|
| Oviedo | 10.3° | 1 min 49 s | 1.015 |
| Leon | 9.7° | 1 min 45 s | 1.013 |
| Palencia | 8.7° | 1 min 42 s | 1.012 |
| Valladolid | 8.6° | 1 min 28 s | 1.007 |
| Burgos | 8.3° | 1 min 44 s | 1.014 |
| Zaragoza | 6.0° | 1 min 24 s | 1.007 |
| Valencia | 4.5° | 1 min 00 s | 1.003 |
| **Palma de Majorque** | **2.6°** | **1 min 36 s** | **1.015** |

Les huit candidates etaient bien dans le trajet de la totalite : c'est verifie,
pas suppose — chacune des huit pages T&D est intitulee « Total Solar Eclipse in
*ville* » et donne un C2 et un C3, ce que les pages partielles voisines (Madrid,
Barcelone, Paris) ne font pas. WP-fr recense en outre Oviedo, Leon, Burgos,
Zaragoza et Palma parmi les localites de la totalite ; Valence, Valladolid et
Palencia n'y figurent pas, cette table n'etant pas exhaustive. L'IGN confirme les
deux villes basses sur ses propres fiches communales : Palma 2.4° et 1 min 36 s,
Valence 4.4° et 0 min 60 s (sic) — hauteurs geometriques, a ne pas comparer
directement a la colonne ci-dessus, qui est apparente.

Palma est retenue parce qu'elle est la seule a cumuler les deux : la hauteur de
Soleil la plus basse de la liste (2.6° de hauteur apparente au maximum, contre
4.5° a Valence et 8.3° a Burgos) **et** une totalite franche — 1 min 36 s,
magnitude 1.015, la plus forte des huit candidates a egalite avec Oviedo, donc
bien a l'interieur du trajet et non sur son bord. Valence, la seule autre a
passer sous les cinq degres, a une totalite marginale : 1 min 00 s et magnitude
1.003, c'est-a-dire tout pres de la limite du trajet. Palma offre une totalite
une fois et demie plus longue, deux degres plus bas.

Coordonnees a saisir dans `build.py`, telles que publiees par l'IGN sur sa fiche
communale de Palma :

| grandeur | valeur publiee (IGN) | conversion decimale |
|---|---|---|
| latitude | 39° 34′ 16.13″ N | 39.571147° N |
| longitude | 2° 39′ 06.54″ E | 2.651817° E |
| altitude | 24 m | 24 m |

La forme sexagesimale est celle qui fait foi ; la colonne decimale n'est qu'une
conversion d'unites. L'IGN precise que ses calculs tiennent compte de l'altitude
du terrain ; il ne precise pas, sur la fiche, quel point de la commune ces
coordonnees designent.

### Circonstances locales

Jeu de reference retenu, en UTC. **Les instants proviennent de T&D** pour les
trois villes : c'est la seule source consultee qui publie les quatre contacts a
la seconde pour les trois, avec une methode identique d'une ville a l'autre. Les
autres sources servent de controle et sont donnees plus bas.

| ville | c1 | c2 | c3 | c4 | magnitude |
|---|---|---|---|---|---|
| Paris | `2026-08-12T17:22:14Z` | *aucun* | *aucun* | `2026-08-12T19:09:28Z` | 0.931 |
| Reykjavik | `2026-08-12T16:47:13Z` | `2026-08-12T17:48:18Z` | `2026-08-12T17:49:18Z` | `2026-08-12T18:47:40Z` | 1.002 |
| Palma | `2026-08-12T17:38:04Z` | `2026-08-12T18:31:06Z` | `2026-08-12T18:32:42Z` | `2026-08-12T19:22:34Z` | 1.015 |

**Paris n'a ni C2 ni C3** : l'eclipse y est partielle, la Lune n'a jamais
entierement couvert le Soleil. Ce n'est pas une lacune de la table, c'est le fait
astronomique. Toute valeur ecrite dans ces deux cases serait fausse.

Instant du maximum et grandeurs au maximum :

| ville | maximum (UTC) | magnitude | obscuration | hauteur apparente du Soleil | hauteur geometrique | azimut |
|---|---|---|---|---|---|---|
| Paris | `2026-08-12T18:17:21Z` | 0.931 (T&D) | 92.1 % / 92.2 % — voir plus bas | 7.7° (T&D) | non publiee | 284° (T&D) |
| Reykjavik | `2026-08-12T17:48:48Z` | 1.002 (T&D) | 100 % (totale) | 24.5° (T&D) | non publiee | 253° (T&D) |
| Palma | `2026-08-12T18:31:54Z` | 1.015 (T&D) | 100.0 % (IGN) | 2.6° (T&D) | 2.4° (IGN) | 287.3° (IGN) |

Les deux colonnes de hauteur ne sont pas deux estimations concurrentes d'une
meme grandeur : voir « Hauteur du Soleil : deux grandeurs, pas deux valeurs »
ci-dessous. La colonne de reference pour un rendu visuel est la hauteur
**apparente**.

Pages T&D utilisees, consultees le 13 aout 2026 :

- <https://www.timeanddate.com/eclipse/in/france/paris?iso=20260812>
- <https://www.timeanddate.com/eclipse/in/iceland/reykjavik?iso=20260812>
- <https://www.timeanddate.com/eclipse/in/spain/palma?iso=20260812>

Les pages T&D donnent l'heure legale locale (CEST = UTC+2 pour Paris et Palma ;
l'Islande est a UTC toute l'annee, sans heure d'ete). La conversion en UTC
ci-dessus est un simple decalage de fuseau.

#### Controles independants, et desaccords

**Palma.** La fiche IGN — source officielle espagnole, calculs de l'Observatorio
Astronomico Nacional — donne, en heure legale : debut 19:38.1, debut de totalite
20:31.1, maximum 20:31.9, fin de totalite 20:32.7, coucher du Soleil 20:49.4, fin
21:22.6 ; duree de la totalite 1 min 36 s, obscuration 100.0 %, hauteur 2.4°
(geometrique, voir plus bas), azimut 287.3°. Soit en UTC : C1 17:38:06, C2 18:31:06, maximum 18:31:54,
C3 18:32:42, C4 19:22:36. **C2, le maximum et C3 tombent a la seconde sur les
valeurs T&D** ; C1 et C4 s'en ecartent de 2 s. Attention toutefois : l'IGN publie
au dixieme de minute, soit une quantification de 6 s — la concordance a la
seconde est en partie un effet de l'arrondi.

WP-fr (donc vigiacosmos.es) donne pour Palma 19:37:59 / 20:31:00 / 20:32:36,
c'est-a-dire **5 a 6 s en avance** sur T&D et l'IGN sur les trois contacts. Un
ecart de cet ordre est exactement ce que la tolerance de 5 s va rencontrer.

#### Hauteur du Soleil : deux grandeurs, pas deux valeurs

Ce fichier signalait initialement, a Palma, un desaccord inexplique sur la
hauteur du Soleil au maximum : 2.4° a l'IGN contre 2.6° chez T&D. **Ce n'etait
pas un desaccord.** Les deux sources publient deux grandeurs differentes du meme
instant :

- **T&D publie la hauteur apparente**, refraction atmospherique comprise — celle
  a laquelle on voit reellement le Soleil ;
- **l'IGN publie la hauteur geometrique**, sans refraction — la direction vraie
  de l'astre.

Pres de l'horizon la refraction releve l'image du Soleil d'environ un quart de
degre ; l'ecart de 0.2° entre les deux chiffres est de cet ordre. Aucune des deux
valeurs n'est fausse, et il n'y a pas a arbitrer entre elles : il faut savoir
laquelle on lit. Precision d'honnetete : **ni l'une ni l'autre des deux pages ne
declare sa convention** — l'attribution ci-dessus est une conclusion, pas une
citation.

Comment cela a ete etabli, en toute transparence sur la provenance : **par notre
propre chaine de calcul**, donc pas par une source publiee. Elle donne pour Palma
au maximum 2.644° de hauteur apparente et 2.389° de hauteur geometrique,
c'est-a-dire les deux chiffres publies a 0.05° pres chacun ; et appliquer
`skyfield.earthlib.refract` a la valeur de l'IGN redonne celle de T&D. Le meme
schema se retrouve aux deux autres sites, ou le Soleil est assez haut pour que la
distinction s'efface : Paris 7.713° calcule contre 7.7° chez T&D, Reykjavik
24.523° contre 24.5°.

Ces trois nombres calcules sont donnes **comme explication de deux valeurs
publiees, jamais comme valeurs de reference**. Ils ne remplacent ni ne corrigent
quoi que ce soit dans les tables ci-dessus, qui restent integralement recopiees
de sources externes. C'est aussi pourquoi `tools/eclipse/VALIDATION.md` classe la
ligne IGN de la hauteur en « info » et l'exclut de son verdict : comparer notre
hauteur apparente a une hauteur geometrique publiee reviendrait a comparer deux
grandeurs distinctes.

**Reykjavik.** IS-sol donne 16:47 / 17:48:19 / 17:48:48 / 17:49:18 / 18:47 : le
debut de totalite tombe a 1 s de T&D, le maximum et la fin de totalite a la
seconde. WP-fr donne 16:47:10 / 17:48:14 / 17:49:12 / 18:47:34, soit 4 a 6 s en
avance, et une totalite de 58 s au lieu de 60 s. L'*Almanak Haskola Islands*,
lui, annonce **1 min 10 s** de totalite a Reykjavik, contre 58 a 60 s pour les
trois autres — douze secondes d'ecart. Ce n'est pas une erreur : Reykjavik est
pres du bord du trajet, la duree y varie tres vite d'un quartier a l'autre, et
les sources ne visent manifestement pas le meme point. Pour comparaison, le meme
almanach donne 1 min 36 s a Isafjordur, et IS-sol 1 min 26 s a Straumsnes et
2 min 13 s a Latrabjarg.

**Paris.** Aucune deuxieme source a la seconde n'a ete trouvee. L'IMCCE et
l'Observatoire de Paris publient bien des circonstances locales, mais uniquement
via un formulaire JavaScript
(<https://ssp.imcce.fr/forms/solar-eclipses/2026-08-12/local-circumstances>,
<https://eclipseop.obspm.fr/>) dont la sortie n'a pas pu etre recuperee ici. Les
valeurs parisiennes ci-dessus reposent donc sur **une seule source**. Les sites
francais secondaires qui citent l'IMCCE s'accordent sur le maximum a 20h17 CEST,
une hauteur de 7.6° et un intervalle 19:22 – 21:09 CEST, ce qui recoupe T&D a la
minute pres, mais ne constitue pas une verification a la seconde.

#### Ce qui n'est pas publie, et qu'on n'invente pas

- **Obscuration de Paris.** Aucune source primaire consultee ne la publie. Deux
  valeurs secondaires circulent : **92.1 %**, attribuee a l'IMCCE
  (<https://eclipse-solaire.fr/eclipse-solaire-2026/paris/>), et **92.2 %**,
  citee par WP-fr d'apres ici.fr. Les deux sont enregistrees telles quelles ; ni
  l'une ni l'autre ne doit servir de reference stricte.
- **Obscuration de Reykjavik.** Non publiee explicitement par les sources
  consultees. Elle vaut 100 % parce que l'eclipse y est totale, ce qui est une
  definition et non une mesure.
- **Coordonnees supposees par T&D.** Les pages d'eclipse de T&D n'indiquent pas
  le point exact utilise pour chaque ville, et ses pages geographiques non plus.
  Pour Paris et Reykjavik, on ne sait donc pas a quel point se rapportent les
  instants retenus. Pour Palma, la concordance a 2 s avec l'IGN suggere que les
  deux points sont voisins, mais ce n'est qu'une presomption.
- **Magnitudes IGN.** L'IGN publie l'obscuration, pas la magnitude.
- **Hauteur du Soleil aux contacts pour Palma cote IGN.** Seule celle du maximum
  est donnee.

#### Quatre pieges de transcription

1. **Le ΔT n'est pas le meme d'une source a l'autre** : 75.4 s (GSFC), 72.4 s
   (EW), 75.319 s (IMCCE), 69.6 s (T&D), non precise (IGN). C'est un decalage
   systematique entre jeux de valeurs, pas du bruit. Avec 5.8 s d'amplitude entre
   les extremes, il est du meme ordre que la tolerance de 5 s : si la validation
   echoue de peu, c'est la premiere chose a regarder, avant de suspecter le code.
2. **Les instants publies valent pour un point precis.** Un chef-lieu s'etend sur
   plusieurs kilometres, et quelques centaines de metres suffisent a deplacer un
   contact de plusieurs secondes — le cas de Reykjavik, pres du bord du trajet,
   le montre a douze secondes pres sur la duree de la totalite. Comparer nos
   valeurs a celles d'une source dont on ignore le point suppose a donc une
   limite intrinseque, quelle que soit la qualite du calcul des deux cotes.
3. **Magnitude et obscuration ne sont pas la meme grandeur.** La magnitude est un
   rapport de longueurs (fraction du diametre solaire couverte), l'obscuration un
   rapport de surfaces. A Paris, magnitude 0.931 et obscuration ~92 % coexistent
   sans se contredire. La clef `magnitude` du dictionnaire de `validate.py` doit
   recevoir la magnitude, pas l'obscuration.
4. **Pres de l'horizon, « hauteur du Soleil » est ambigu tant que la source ne
   dit pas si la refraction est comprise.** A Palma l'ecart entre hauteur
   apparente et hauteur geometrique vaut 0.25° sur une hauteur de 2.6°, soit
   pres de 10 % : il ne se noie dans aucune tolerance raisonnable. A Reykjavik,
   Soleil a 24.5°, il devient invisible. C'est donc exactement aux sites qui
   nous interessent le plus — ceux ou l'eclipse se joue au ras de l'horizon —
   que le piege se referme. Qui reverifie ces nombres doit d'abord etablir la
   convention de chaque source, avant de conclure a une erreur.

Enfin, un detail qui compte pour le rendu : **a Palma, C4 (19:22:36 UTC) survient
apres le coucher du Soleil (20:49.4 en heure legale, soit 18:49:24 UTC, IGN ;
18:49:22 UTC selon T&D)**. L'IGN imprime d'ailleurs ces phases
en rouge sur sa fiche, avec la mention qu'elles ne sont pas observables, le
centre du Soleil etant sous l'horizon. A Paris, C4 (19:09:28 UTC) precede le
coucher (19:11:23 UTC) de moins de deux minutes, Soleil a 0.0° de hauteur : la
fin de l'eclipse s'y joue dans la refraction. A Reykjavik, C4 a lieu Soleil haut
de 18.2°, sans difficulte.
