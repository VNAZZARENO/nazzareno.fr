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

Trois longueurs d'onde de la table, choisies au plus proche des primaires sRGB.

| canal | λ (Å) | λ (nm) | A(2) | B(2) | C(2) | u1 | u2 |
|---|---|---|---|---|---|---|---|
| rouge | 6109.75 | 610.975 | 0.34653 | 0.92982 | −0.27635 | **0.37712** | **0.27635** |
| vert  | 5522.00 | 552.200 | 0.29462 | 0.98032 | −0.27494 | **0.43044** | **0.27494** |
| bleu  | 4683.06 | 468.306 | 0.21495 | 0.99746 | −0.21241 | **0.57264** | **0.21241** |

Les trois lignes verifient `A + B + C = 1.00000` exactement, ce qui sert de
controle de transcription. (La ligne 4719.00 Å, autre candidate pour le bleu, a
ete ecartee : sa somme vaut 1.00040 dans le fac-simile, signe d'un chiffre
douteux a la numerisation. La ligne 5199.30 Å est manifestement corrompue,
somme 2.00000.)

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

## Instants de contact publies par la NASA

À completer (tache ulterieure).
