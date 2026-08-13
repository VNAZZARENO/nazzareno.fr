// Fragment shader de l'encart teleobjectif.
//
// Le grand panneau montre la LUMIERE: ce que le ciel devient quand le Soleil
// s'eteint. Cet encart-ci montre la GEOMETRIE: les deux disques a leur vraie
// taille apparente, a leur vraie position relative. C'est la que le lecteur
// peut verifier que la simulation ne triche pas -- a Paris la Lune doit mordre
// le Soleil sans jamais le couvrir, a Palma le couvrir entierement.
//
// Cinq decisions, toutes declarees:
//
// 1. LA COURBE DE TRANSFERT ET L'EXPOSITION SONT CELLES DU CIEL. Elles
//    viennent du fragment TONALITE de sky.glsl.js, importe tel quel: une seule
//    definition pour toute la page. Deux copies finiraient par diverger, et
//    l'encart et le ciel raconteraient deux histoires differentes sur la meme
//    image sans que rien ne le signale.
//
// 2. LA PHOTOSPHERE EST VUE A TRAVERS UN FILTRE NEUTRE. On ne regarde pas le
//    Soleil sans filtre, et un instrument qui le ferait ne rendrait qu'un
//    disque blanc ecrete: le centre du disque est 4700 fois au-dessus du BLANC
//    de la courbe de transfert, soit douze diaphragmes, donc l'assombrissement
//    centre-bord -- tout le sujet du point 1 de la tache -- serait
//    rigoureusement invisible. L'encart porte donc un filtre FIXE de densite
//    4,5, jamais adapte a l'image ni a l'instant. C'est un choix
//    d'INSTRUMENT, pas une auto-exposition.
//
//    Il faut dire ce que ce filtre ne rachete pas: meme correctement exposee,
//    la variation centre-bord reste DISCRETE a l'ecran (sRGB 237 au centre,
//    231 au bord mesures sur le rendu), parce que la courbe est logarithmique
//    et qu'un rapport de 1,5 en luminance ne vaut que 0,6 diaphragme. Elle se
//    lit surtout en couleur: le canal bleu descend a 221 quand le rouge tient
//    a 234, donc le limbe est plus chaud -- exactement ce que dit la prose de
//    la page sur le flux residuel.
//
// 3. LA COURONNE, ELLE, EST SANS FILTRE. C'est exactement le montage de toute
//    image d'eclipse publiee: la photosphere ne se photographie qu'a travers
//    un filtre, la couronne qu'une fois le filtre retire. Les deux ne
//    coexistent jamais dans une seule pose -- il y a six ordres de grandeur
//    entre elles. La couronne n'a donc AUCUN gain arbitraire: sa luminance
//    physique passe directement dans l'exposition et la courbe du ciel.
//
// 4. LE FOND N'EST PAS LE CIEL, c'est le champ noir de l'instrument filtre.
//    L'encart ne refait pas le raymarch atmospherique du grand panneau: a
//    travers un filtre de densite 4,5, un ciel de plein jour tombe de toute
//    facon sous le premier niveau de sortie. Ce qui reste noir est noir pour
//    une raison, pas par commodite.
//
// 5. L'EXTINCTION ATMOSPHERIQUE N'EST PAS APPLIQUEE ICI, et c'est la seule
//    divergence assumee avec le grand panneau. A Palma le Soleil est a 2,6 deg
//    de hauteur, donc sous une vingtaine de masses d'air: le vrai disque y
//    etait rouge sombre et la vraie couronne bien plus faible que ce que
//    l'encart montre. La corriger rendrait l'encart de Palma quasi illisible,
//    or son role est de faire verifier une GEOMETRIE, pas de refaire la
//    photometrie que le panneau de gauche traite deja.

import { SRGB_LIMB_COEFFS } from './flux.js';
import { TONALITE } from './sky.glsl.js';

// Champ de l'encart, en degres. Le Soleil fait 0,526 deg de diametre: il
// occupe un tiers du cadre, et il reste de la place pour la couronne jusqu'a
// 2,8 rayons solaires sur les cotes.
export const CHAMP_DEG = 1.5;

// (u1, u2) par canal, dans l'ordre (rouge, vert, bleu). MEME table que la LUT
// de flux et que le pipeline hors ligne (Pierce & Slaughter 1977): l'encart
// dessine le disque avec la loi qui a servi a calculer l'obscuration affichee
// a cote. Interpole depuis flux.js, jamais recopie a la main.
const composante = (i) => SRGB_LIMB_COEFFS.map((c) => c[i].toFixed(5)).join(', ');

export const INSET_FS = `#version 300 es
precision highp float;
out vec4 sortie;

uniform vec4 uZone;        // x, y, largeur, hauteur de l'encart, en pixels
uniform vec2 uLune;        // decalage Lune - Soleil, en RADIANS, dans le plan
                           // tangent a la direction du Soleil (x vers l'est,
                           // y vers le zenith local)
uniform float uRSoleil;    // rayon apparent du Soleil, en radians
uniform float uRLune;      // rayon apparent de la Lune, en radians
uniform vec3 uFlux;        // flux visible chez l'observateur (1 = disque entier)
uniform vec3 uBordure;     // couleur du lisere, deja en sRGB

${TONALITE}

const float PI = 3.14159265358979;
const float TAU = 6.28318530717959;
const float CHAMP = radians(${CHAMP_DEG.toFixed(3)});

const vec3 U1 = vec3(${composante(0)});
const vec3 U2 = vec3(${composante(1)});

// Filtre neutre de l'encart: densite 4,5. Voir la decision 2 en tete de
// fichier. Cette valeur ne depend ni de l'instant, ni du lieu, ni du contenu
// de l'image; elle place le centre du disque vers sRGB 0,93, sous l'ecretage,
// donc l'assombrissement centre-bord est rendu au lieu d'etre efface.
const float FILTRE = 3.0e-5;

// -- bruit --------------------------------------------------------------------
// Bruit de valeur PERIODIQUE en x. La periode n'est pas un detail: la premiere
// coordonnee est toujours un angle polaire, et un bruit non periodique
// laisserait une couture nette a theta = +/- PI, en plein milieu de la
// couronne et du limbe lunaire.
float alea(vec2 cellule, float periode) {
  cellule.x = mod(cellule.x, periode);
  return fract(sin(dot(cellule, vec2(127.1, 311.7))) * 43758.5453123);
}

float bruit(vec2 p, float periode) {
  vec2 i = floor(p);
  vec2 f = p - i;
  f = f * f * (3.0 - 2.0 * f);
  float a = alea(i, periode);
  float b = alea(i + vec2(1.0, 0.0), periode);
  float c = alea(i + vec2(0.0, 1.0), periode);
  float d = alea(i + vec2(1.0, 1.0), periode);
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// -- couronne -----------------------------------------------------------------
// Profil radial empirique K+F de van de Hulst / Baumbach. r en rayons solaires.
// Ce n'est PAS une observation: la page le declare explicitement.
float couronne(float r) {
  if (r < 1.0) return 0.0;
  return 1e-6 * (0.0532 * pow(r, -2.5) + 1.425 * pow(r, -7.0) + 2.565 * pow(r, -17.0));
}

// Jets coronaux, en coordonnees polaires: le detail porte sur l'ANGLE, le
// rayon n'entre qu'en logarithme et faiblement, ce qui etire les structures
// radialement -- c'est la forme des jets. Aout 2026 tombe pres du maximum
// solaire, ou la couronne est a peu pres ronde et herissee de jets sur tout le
// pourtour: pas d'aplatissement equatorial a modeliser.
//
// STYLISATION ASSUMEE: ce champ est du bruit procedural, pas une prevision de
// la couronne du 12 aout 2026, que personne ne sait faire.
const float JETS = 9.0;   // secteurs de la premiere octave

float jets(float r, float theta) {
  vec2 p = vec2(theta / TAU * JETS, log(r) * 0.7);
  float somme = 0.0;
  float amplitude = 0.5;
  float periode = JETS;
  for (int i = 0; i < 4; i++) {
    somme += amplitude * bruit(p, periode);
    p *= 2.0;
    periode *= 2.0;
    amplitude *= 0.5;
  }
  // somme parcourt a peu pres [0, 0.94], de moyenne 0.47: le motif va donc de
  // 0,35 a 2,2 environ. Cet ecart n'est pas gratuit: entre un jet equatorial et
  // un trou coronal polaire, le rapport de brillance est bien de l'ordre de 5.
  float motif = 0.35 + 2.0 * somme;
  // Le contraste azimutal croit avec le rayon. Pres du limbe la couronne est
  // presque uniforme -- c'est la couronne K, diffusee par des electrons denses
  // et bien melanges -- et ce sont les couches externes qui se structurent en
  // jets. Cela laisse aussi l'anneau interieur propre, la ou se joue la lecture
  // geometrique de l'encart.
  return mix(1.0, motif, smoothstep(1.0, 1.8, r));
}

// Visibilite de la couronne. Physiquement la couronne brille toujours autant:
// ce qui la revele, c'est l'extinction de tout le reste. L'encart ne modelise
// ni la lumiere parasite de l'instrument ni celle de l'atmosphere, qui sont ce
// qui la noie reellement pendant les phases partielles; on les remplace par ce
// fondu, pilote par le FLUX VISIBLE REEL. Le moment ou la couronne apparait
// est donc juste, la facon dont elle apparait est une stylisation.
//
// Seuils lus sur les donnees: au deuxieme contact a Palma le flux vaut 3,9e-5,
// dix secondes avant 9,7e-4, une minute avant 1,5e-2. La couronne monte donc
// sur la derniere minute. A Paris, dont le flux ne descend jamais sous 5,4e-2,
// elle ne parait jamais -- et c'est le comportement voulu.
float visibiliteCouronne(float flux) {
  return 1.0 - smoothstep(2.0e-4, 6.0e-3, flux);
}

// -- limbe lunaire ------------------------------------------------------------
// Relief du limbe. L'amplitude est REELLE dans son ordre de grandeur: les
// montagnes et les vallees du limbe lunaire couvrent environ 2 secondes d'arc,
// soit 0,2 % du rayon apparent. Le PROFIL, lui, est du bruit procedural: ce
// n'est pas le limbe reel de la Lune du 12 aout 2026, qui se lit dans les
// donnees altimetriques de LRO et que cette page n'utilise pas.
//
// C'est ce relief qui produit les grains de Baily: partout ailleurs il est
// 400 fois plus fin qu'un pixel de l'encart et rigoureusement invisible, mais
// au voisinage des deuxieme et troisieme contacts le croissant restant est du
// meme ordre, et il se brise en chapelet. Le MOMENT est donc vrai, le dessin
// des grains ne l'est pas.
const float RELIEF = 0.0022;

float rayonLune(float theta) {
  vec2 p = vec2(theta / TAU * 32.0, 0.5);
  float somme = 0.0;
  float amplitude = 0.5;
  float periode = 32.0;
  for (int i = 0; i < 3; i++) {
    somme += amplitude * (bruit(p, periode) - 0.5);
    p.x *= 2.0;
    periode *= 2.0;
    amplitude *= 0.5;
  }
  return uRLune * (1.0 + RELIEF * 2.0 * somme);
}

// -- anneau de diamant --------------------------------------------------------
// Fenetre temporelle de l'eclat, sur le flux visible. Elle s'ouvre des que le
// Soleil n'est plus tout a fait eteint et se referme des qu'il en reste plus
// qu'un filet: sur les donnees de Palma, cela couvre environ huit secondes de
// part et d'autre de chaque contact interieur. Le MOMENT est reel; l'eclat
// lui-meme est une stylisation (un instrument reel le doit a sa propre
// diffusion, que l'encart ne modelise pas).
// La decroissance est EXPONENTIELLE et courte, et ce n'est pas un reglage a
// vue: la courbe de transfert etant logarithmique, une loi de puissance -- ou
// simplement une exponentielle plus large -- garderait a un rayon lunaire de
// l'eclat de quoi eclairer tout le disque de la Lune en gris moyen. Une Lune
// grise serait un contresens: elle est opaque, c'est le sujet de l'encart. A
// 0,02 deg de largeur, l'eclat perd six ordres de grandeur sur un rayon
// lunaire et le disque reste noir.
const float GLARE = 8.0;                       // luminance au coeur de l'eclat
const float LARGEUR_GLARE = radians(0.020);    // decroissance exponentielle

float fenetreDiamant(float flux) {
  return smoothstep(0.0, 1.0e-5, flux) * (1.0 - smoothstep(1.0e-4, 8.0e-4, flux));
}

void main() {
  vec2 uv = (gl_FragCoord.xy - uZone.xy) / uZone.zw;

  // Lisere d'un pixel: il separe le champ noir de l'encart du ciel qui
  // l'entoure, dans les deux schemas de couleur de la page.
  vec2 pixels = min(gl_FragCoord.xy - uZone.xy, uZone.xy + uZone.zw - gl_FragCoord.xy);
  if (min(pixels.x, pixels.y) < 1.0) {
    sortie = vec4(uBordure, 1.0);
    return;
  }

  // Plan tangent centre sur le Soleil, en radians. x vers l'est, y vers le
  // zenith local: le meme sens que le grand panneau, ou l'azimut croit vers la
  // droite et la hauteur vers le haut.
  vec2 p = (uv - 0.5) * CHAMP;

  // Un demi-pixel d'angle: sert d'antialiasage analytique sur les deux bords.
  // Ce n'est pas cosmetique. Pres des contacts interieurs, le croissant de
  // photosphere qui reste est bien plus fin qu'un pixel (0,0008 deg contre
  // 0,015 deg par pixel dix secondes avant C2): un test binaire l'effacerait
  // purement et simplement, et avec lui l'anneau de diamant. La couverture
  // partielle du pixel est ce qu'un vrai capteur integre.
  float aa = 0.5 * CHAMP / uZone.z;

  // Deux angles polaires, et il ne faut pas les confondre: celui du limbe
  // lunaire se mesure autour du centre de la LUNE, celui des jets coronaux
  // autour du centre du SOLEIL.
  float rho = length(p);
  vec2 q = p - uLune;
  float thetaLune = atan(q.y, q.x);
  float thetaSoleil = atan(p.y, p.x);

  // Couverture par la Lune: 1 = pixel entierement hors du disque lunaire.
  float horsLune = smoothstep(-aa, aa, length(q) - rayonLune(thetaLune));

  vec3 lumiere = vec3(0.0);

  // 1. Photosphere. mu = cos de l'angle au centre du disque, et la loi
  // quadratique I(mu)/I(1) = 1 - u1 (1-mu) - u2 (1-mu)^2, par canal.
  //
  // La normalisation n'est pas libre: l'irradiance hors atmosphere vaut 1 par
  // canal dans tout le pipeline, donc la luminance au centre du disque vaut
  // 1 / (PI r^2 (1 - u1/3 - u2/6)) -- le denominateur etant la moyenne de la
  // loi sur le disque. L'encart ne choisit donc aucun niveau: il herite de
  // celui du reste de la page, au filtre pres.
  float dansSoleil = 1.0 - smoothstep(-aa, aa, rho - uRSoleil);
  if (dansSoleil > 0.0) {
    float mu = sqrt(max(0.0, 1.0 - (rho / uRSoleil) * (rho / uRSoleil)));
    vec3 profil = 1.0 - U1 * (1.0 - mu) - U2 * (1.0 - mu) * (1.0 - mu);
    vec3 centre = 1.0 / (PI * uRSoleil * uRSoleil * (1.0 - U1 / 3.0 - U2 / 6.0));
    lumiere += FILTRE * centre * profil * dansSoleil * horsLune;
  }

  // 2. Couronne. r en rayons solaires; la loi rend une fraction de la
  // BRILLANCE MOYENNE du disque, d'ou le facteur 1/(PI r^2) qui la ramene dans
  // les memes unites que tout le reste. Aucun gain arbitraire. La Lune
  // l'occulte comme elle occulte la photosphere: elle est devant.
  float r = rho / uRSoleil;
  if (r > 1.0) {
    float brillanceMoyenne = 1.0 / (PI * uRSoleil * uRSoleil);
    float k = couronne(r) * brillanceMoyenne * jets(r, thetaSoleil)
            * visibiliteCouronne(dot(uFlux, LUMA)) * horsLune;
    lumiere += vec3(k);
  }

  // 3. Anneau de diamant. Le dernier point de photosphere visible est celui du
  // limbe solaire le plus eloigne du centre de la Lune, c'est-a-dire a
  // l'oppose du decalage lunaire: aucune position ad hoc n'est choisie ici.
  float diamant = fenetreDiamant(dot(uFlux, LUMA));
  if (diamant > 0.0 && length(uLune) > 1.0e-9) {
    vec2 eclat = -uRSoleil * normalize(uLune);
    lumiere += vec3(GLARE * diamant * exp(-length(p - eclat) / LARGEUR_GLARE));
  }

  sortie = vec4(versSRGB(tonalite(lumiere * EXPOSITION)), 1.0);
}`;
