// Fragment shader du ciel, en projection equidistante.
//
// Trois decisions structurent ce fichier, et elles ne sont pas negociables au
// coup par coup:
//
// 1. La projection est equidistante -- l'azimut est lineaire en x, la hauteur
//    lineaire en y. L'horizon reste donc une droite et les bords ne s'etirent
//    pas, contrairement a une projection rectilineaire a 120 degres de champ.
//    Le prix a payer est une compression de l'azimut pres du zenith; a 40
//    degres de hauteur elle vaut 23 %, ce qui ne se voit pas sur un ciel.
//
// 2. La diffusion est integree le long du rayon de visee seulement: la
//    transmittance vers le Soleil est lue dans la LUT plutot que marchee, et
//    les ordres superieurs a 1 viennent eux aussi d'une LUT (tache 19). Un
//    rayon secondaire par pas couterait 32 fois plus cher pour une image que
//    personne ne saurait distinguer.
//
// 3. L'exposition est FIXE, et la courbe de transfert aussi. Pas
//    d'auto-exposition, pas d'adaptation temporelle, pas de dependance au
//    contenu de l'image. La page montre deux lieux cote a cote et le sujet
//    meme de la page est que l'un s'assombrit et pas l'autre: une
//    auto-exposition relevrait le lieu sombre et effacerait exactement ce
//    qu'il y a a voir.

import { ATMOSPHERE, TRANSMITTANCE_LUT } from './atmosphere.glsl.js';
import { LUT_D, LUT_RATIO, RATIO_MIN, RATIO_MAX, D_MAX } from './flux.js';

// Exposition FIXE, calibree une fois pour toutes: elle ne fait que porter la
// luminance physique dans le domaine ou la courbe de transfert travaille. Les
// unites sont arbitraires -- l'irradiance solaire hors atmosphere vaut 1 par
// canal -- donc ce nombre n'a de sens que relativement a elle.
const EXPOSITION = 40.0;

export const SKY_FS = `#version 300 es
precision highp float;
precision highp sampler2D;
out vec4 sortie;

uniform vec4 uZone;             // x, y, largeur, hauteur du panneau, en pixels
uniform vec3 uSoleil;           // direction unitaire vers le Soleil
uniform vec3 uLune;             // direction unitaire vers la Lune
uniform vec3 uFlux;             // flux visible CHEZ L'OBSERVATEUR (1 = disque entier)
uniform float uRSoleil;         // rayon apparent du Soleil, en radians
uniform float uRLune;           // rayon apparent de la Lune, en radians
uniform float uDSoleilKm;       // distance du Soleil, en KILOMETRES (source: JPL)
uniform float uDLuneKm;         // distance de la Lune, en KILOMETRES (source: JPL)
uniform float uAzimutCentre;    // azimut vise au centre du panneau, en radians
uniform float uAltitudeObs;     // altitude de l'observateur, en metres
uniform sampler2D uMultiScatter;
uniform sampler2D uFluxLut;

${ATMOSPHERE}
${TRANSMITTANCE_LUT}

// Champ de vision. On borne la hauteur a 90 degres et on en deduit la largeur,
// de sorte que l'echelle reste la meme sur les deux axes quel que soit le
// format du panneau: un panneau large plafonne a 120 degres d'azimut, un
// panneau haut (deux lieux empiles sur mobile) ne part pas au-dela du zenith.
const float FOV_H_MAX = radians(120.0);
const float FOV_V_MAX = radians(90.0);

// Fraction de la hauteur du panneau situee sous l'horizon. Le sol occupe le bas
// du cadre sans le devorer: le ciel est le sujet.
const float HORIZON = 0.22;

const int PAS = 32;             // pas du raymarch principal
const int PAS_AMBIANT = 8;      // pas de l'estimation du ciel vu par le sol
const float EXPOSITION = ${EXPOSITION.toFixed(1)};

// Parametrage de la LUT de flux, repris tel quel de flux.js -- ces valeurs ne
// sont pas recopiees a la main, elles sont interpolees depuis le module qui
// construit la table. Si elle change de taille ou de bornes, le shader suit.
const float LUT_D = ${LUT_D}.0;
const float LUT_RATIO = ${LUT_RATIO}.0;
const float RATIO_MIN = ${RATIO_MIN.toFixed(6)};
const float RATIO_MAX = ${RATIO_MAX.toFixed(6)};
const float D_MAX = ${D_MAX.toFixed(6)};

// Somme de tous les ordres de diffusion superieurs a 1, lue dans la LUT
// construite par luts.js. Parametrage identique a la construction:
// x = (cosSoleil + 1) / 2, y = alt / (R_ATMO - R_SOL). La valeur rendue est
// une luminance PAR UNITE de coefficient de diffusion: c'est a l'appelant de
// la multiplier par sigma_s local.
vec3 diffusionMultiple(float alt, float cosSoleil) {
  vec2 uv = vec2(cosSoleil * 0.5 + 0.5, alt / (R_ATMO - R_SOL));
  return texture(uMultiScatter, clamp(uv, 0.0, 1.0)).rgb;
}

// Position de l'observateur dans le repere planetocentrique du raymarch.
// C'est l'origine a laquelle tous les deplacements de fluxAuPoint sont
// rapportes -- y compris ceux du ciel estime depuis un point du sol, qui part
// d'une autre origine mais reste evalue dans le meme cone d'ombre.
vec3 positionObservateur() {
  return vec3(0.0, R_SOL + uAltitudeObs, 0.0);
}

// Fraction du disque solaire encore visible DEPUIS UN POINT DONNE de
// l'atmosphere, par canal. C'est le coeur de toute la page.
//
// Une eclipse ne se rend pas en attenuant le Soleil chez l'observateur: sous
// l'ombre, la lumiere du ciel vient d'AILLEURS -- d'une atmosphere hors de
// l'ombre, a des dizaines de kilometres. C'est exactement ce qui produit
// l'anneau de crepuscule tout autour de l'horizon, signature visuelle de la
// totalite. Il faut donc connaitre la fraction visible en chaque point du
// rayon, pas seulement au point de vue.
//
// Formulation, exacte au premier ordre et tres bon marche: un deplacement
// Delta du point d'echantillonnage par rapport a l'observateur decale la
// direction apparente de la Lune de -Delta_perp / D_lune, et celle du Soleil
// de -Delta_perp / D_soleil. Comme D_lune vaut environ 3.8e5 km contre 1.5e8
// km pour D_soleil, c'est la Lune qui domine. La separation apparente en P
// vaut donc
//     |(u_soleil - u_lune) + Delta_perp * (1/D_lune - 1/D_soleil)|
// Le cone d'ombre, sa largeur d'une centaine de kilometres au sol et son
// inclinaison tombent de cette seule expression, sans aucune geometrie ad hoc.
//
// Deux precisions qui ne sont pas des oublis:
//
// 1. Les distances arrivent en KILOMETRES (elles viennent du JSON, donc des
//    ephemerides du JPL) alors que le raymarch travaille en METRES. D'ou le
//    facteur 1000 ci-dessous: s'en passer changerait la taille de l'ombre de
//    trois ordres de grandeur.
//
// 2. d est calcule comme la longueur de la difference de deux vecteurs
//    unitaires: c'est une CORDE, pas un angle. Pour des angles de l'ordre du
//    degre les deux coincident a mieux que 1e-5 en relatif, tres au-dessous de
//    la resolution de la LUT. L'identification est deliberee.
//
// La conversion separation -> flux est faite par la LUT de flux, construite
// avec le meme modele d'assombrissement centre-bord que le pipeline hors ligne
// a utilise pour l'observateur: atmosphere et observateur sont donc eclaires
// par rigoureusement le meme Soleil.
vec3 fluxAuPoint(vec3 p) {
  vec3 delta = p - positionObservateur();
  // Composante perpendiculaire a la ligne de visee. Soleil et Lune sont a
  // moins d'un degre l'un de l'autre: une seule reference suffit.
  vec3 perp = delta - uSoleil * dot(delta, uSoleil);

  float parallaxe = 1.0 / (uDLuneKm * 1000.0) - 1.0 / (uDSoleilKm * 1000.0);
  float d = length((uSoleil - uLune) + perp * parallaxe);

  // Echantillonnage au CENTRE des texels: flux.js place la valeur d'indice i
  // en d = i/(LUT_D-1) * D_MAX, donc la coordonnee normalisee doit etre
  // remise a l'echelle (LUT_D-1)/LUT_D et decalee d'un demi-texel. Sans cela
  // la table entiere serait lue avec un biais d'un demi-texel.
  float x = clamp(d / (uRSoleil * D_MAX), 0.0, 1.0);
  float y = clamp((uRLune / uRSoleil - RATIO_MIN) / (RATIO_MAX - RATIO_MIN), 0.0, 1.0);
  vec2 uv = vec2(
    (x * (LUT_D - 1.0) + 0.5) / LUT_D,
    (y * (LUT_RATIO - 1.0) + 0.5) / LUT_RATIO
  );
  return texture(uFluxLut, uv).rgb;
}

// Rayon du voisinage dont provient la lumiere diffusee plusieurs fois.
// Cinquante kilometres est l'ordre de grandeur du libre parcours d'un photon
// qui a deja rebondi deux ou trois fois dans la basse atmosphere, et c'est
// aussi l'ordre de grandeur de la demi-largeur de l'ombre lunaire: les deux
// coincident, et c'est precisement ce qui rend l'anneau de crepuscule visible.
const float RAYON_VOISINAGE = 50000.0;

// Flux solaire MOYEN sur le voisinage du point, par canal.
//
// APPROXIMATION DELIBEREE, et declaree comme telle sur la page. La LUT de
// diffusion multiple suppose un Soleil UNIFORME sur tout le voisinage, ce
// qu'une eclipse viole exactement: sous l'ombre, la lumiere qui a rebondi
// plusieurs fois vient d'une region large d'une centaine de kilometres, dont
// une partie est hors de l'ombre. Moduler ce terme par le flux AU POINT
// eteindrait donc le ciel bien trop vite. On le module par une moyenne sur
// quatre points decales de +/- 50 km horizontalement, ce qui restitue le bon
// comportement -- l'ombre ne devient jamais un trou noir -- sans pretendre a
// une resolution du transfert radiatif sous un Soleil non uniforme.
vec3 fluxVoisinage(vec3 p) {
  vec3 n = normalize(p);
  // Deux directions horizontales orthogonales en p. La reference (le nord du
  // repere) n'est jamais colineaire a n: n pointe vers le zenith local, donc
  // presque +y.
  vec3 e1 = normalize(cross(n, vec3(0.0, 0.0, 1.0)));
  vec3 e2 = cross(n, e1);
  return 0.25 * (
      fluxAuPoint(p + e1 * RAYON_VOISINAGE)
    + fluxAuPoint(p - e1 * RAYON_VOISINAGE)
    + fluxAuPoint(p + e2 * RAYON_VOISINAGE)
    + fluxAuPoint(p - e2 * RAYON_VOISINAGE)
  );
}

// Diffusion le long d'un rayon: ordre 1 avec les vraies phases, ordres
// superieurs par la LUT. Rend la lumiere diffusee vers l'observateur, et par
// transmittance l'attenuation totale du rayon -- c'est elle qui donne la
// perspective aerienne quand le rayon finit au sol.
vec3 diffusion(vec3 origine, vec3 dir, float portee, int pas, out vec3 transmittance) {
  float cosTheta = dot(dir, uSoleil);
  float phaseR = phaseRayleigh(cosTheta);
  float phaseM = phaseMie(cosTheta);

  vec3 lumiere = vec3(0.0);
  transmittance = vec3(1.0);

  float precedent = 0.0;
  for (int i = 0; i < pas; i++) {
    // Repartition quadratique: les pas se resserrent pres de l'observateur, ou
    // l'air est le plus dense. Une repartition uniforme gaspillerait la moitie
    // des pas dans le vide du sommet de l'atmosphere, et laisserait le premier
    // kilometre -- celui qui compte -- a un seul echantillon.
    float k = float(i + 1) / float(pas);
    float suivant = portee * k * k;
    float dt = suivant - precedent;
    vec3 p = origine + dir * (0.5 * (precedent + suivant));
    precedent = suivant;

    float h = max(0.0, length(p) - R_SOL);
    vec3 d = densites(h);
    vec3 sigmaE = max(extinction(h), vec3(1e-9));
    float cosSoleil = dot(normalize(p), uSoleil);
    vec3 versSoleil = transmittanceVers(h, cosSoleil);

    // Ordre 1: le Soleil direct, avec les vraies fonctions de phase. Le flux
    // est evalue ICI, au point d'echantillonnage, et non chez l'observateur:
    // c'est cette seule ligne qui fait la difference entre un ciel
    // uniformement attenue et une vraie eclipse.
    vec3 source = versSoleil * fluxAuPoint(p)
                * (BETA_RAYLEIGH * d.x * phaseR + BETA_MIE * d.y * phaseM);
    // Ordres superieurs: la LUT rend deja une luminance ambiante, il ne reste
    // qu'a la diffuser vers l'oeil avec le sigma_s local. Sa modulation par le
    // flux passe par le VOISINAGE (voir fluxVoisinage): ces photons-la ont
    // parcouru des dizaines de kilometres avant d'arriver ici.
    source += diffusionMultiple(h, cosSoleil) * diffusionTotale(h) * fluxVoisinage(p);

    // Integration analytique de la diffusion sur le pas (Hillaire 2020):
    // exacte a extinction constante sur le segment, elle supprime le banding
    // qu'une simple somme au point milieu laisse voir dans les degrades.
    vec3 attenuation = exp(-sigmaE * dt);
    lumiere += transmittance * (source - source * attenuation) / sigmaE;
    transmittance *= attenuation;
  }
  return lumiere;
}

// Sol: un plan analytique, volontairement abstrait. Pas de relief, pas de
// texture, pas d'ombres portees -- le sujet de cette page est le ciel, et un
// sol detaille ne ferait que mentir sur ce qui est calcule.
vec3 sol(vec3 p) {
  vec3 n = normalize(p);
  float cosSoleil = dot(n, uSoleil);
  // Ici, et ici seulement, on garde le flux de l'observateur: le sol visible
  // est a l'altitude de l'observateur et a quelques kilometres au plus, donc
  // la fraction locale y est la sienne. C'est aussi la valeur exacte issue du
  // pipeline hors ligne, qu'on ne va pas remplacer par une lecture de LUT.
  vec3 direct = transmittanceVers(0.0, cosSoleil) * max(cosSoleil, 0.0) * uFlux;

  // Eclairement du ciel, approxime au premier ordre par un ciel uniforme ayant
  // la luminance du zenith: E = pi * L. Le sol ne merite pas une integrale
  // d'hemisphere par pixel, mais il lui faut cet apport: sans lui, tout ce qui
  // n'est pas au soleil devient un noir plat, ce qui est faux.
  vec3 ignore;
  vec3 zenith = diffusion(p + n, n, R_ATMO - R_SOL, PAS_AMBIANT, ignore);

  return ALBEDO_SOL / PI * (direct + PI * zenith);
}

// Courbe de transfert: la reponse de l'OEIL, pas celle d'un appareil photo.
//
// Ce que le calcul produit est une luminance physique. Une courbe filmique
// ordinaire (Hable) sur une exposition calibree en plein jour la restituait
// litteralement: Paris a son maximum rendait cinq fois plus sombre qu'un ciel
// normal, ce qui est exact -- et faux comme image. C'est ce qu'enregistrerait
// un appareil a reglage fixe; la page, elle, raconte ce qu'a vu un temoin, et
// a 92 % d'obscuration un temoin voyait une soiree ordinaire parce que son oeil
// adapte environ quatre diaphragmes. Voir la spec, section 4.5.
//
// Forme retenue: log(1 + K*L), normalisee. C'est la compression de
// Weber-Fechner, la reponse la plus simple qui soit reellement celle d'un oeil,
// et elle a les proprietes qu'il faut: monotone, exactement nulle en zero, et
// elle n'atteint 1 qu'en BLANC, tres au-dessus de tout ce que ce ciel produit
// -- donc aucune haute lumiere ne s'ecrete, meme en plein Soleil.
//
// K = 1000 est calibre sur une seule mesure: entre Paris en plein Soleil et
// Paris au maximum, la scene perd 5,1 diaphragmes; la courbe n'en laisse que
// 0,95 a l'ecran. Elle reproduit donc les quatre diaphragmes d'adaptation de
// l'oeil, ce qui est exactement ce qu'on lui demande -- et pas un reglage a
// vue. BLANC = 160 ne fait que placer le plein jour vers sRGB 0,80.
//
// Un seul jeu de constantes, applique a TOUS les instants et aux DEUX
// panneaux. Rien ne s'adapte au contenu de l'image: ce n'est pas une
// auto-exposition, c'est une fonction fixe et annoncee.
const float K_OEIL = 1000.0;
const float BLANC = 160.0;
const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);
const float DESATURATION = 0.55;

// La courbe s'applique a la LUMINANCE, et les trois canaux sont ensuite remis
// dans leur rapport d'origine. Appliquee canal par canal, une courbe aussi
// logarithmique ecraserait les rapports entre canaux et pousserait tout vers
// le blanc: le ciel haut de Paris, dont le bleu vaut quatre fois le rouge en
// luminance physique, ne le vaudrait plus que 1,25 fois a l'ecran -- du gris.
// Sur la luminance seule, le rapport survit, et l'anneau de crepuscule de la
// totalite garde son bleu profond.
//
// Conserver le rapport des canaux TEL QUEL ne marche pas non plus: un ciel
// bleu profond a B/Y = 2,2, et une fois sa luminance remontee a 0,52 le canal
// bleu vaudrait 1,12 -- hors du gamut sRGB, sur plus de la moitie de l'image.
// On desature donc d'autant plus que le pixel est clair, ce que fait aussi
// l'oeil: les noirs gardent toute leur couleur, les hautes lumieres tirent
// vers le blanc. C'est une fonction du pixel lui-meme, pas de l'image: rien
// ici ne regarde le contenu du cadre.
vec3 tonalite(vec3 lumiere) {
  float luminance = max(dot(lumiere, LUMA), 1e-9);
  float compressee = log(1.0 + K_OEIL * luminance) / log(1.0 + K_OEIL * BLANC);
  vec3 chroma = lumiere / luminance;
  return compressee * pow(chroma, vec3(1.0 - DESATURATION * compressee));
}

vec3 versSRGB(vec3 c) {
  c = clamp(c, 0.0, 1.0);
  return mix(12.92 * c, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}

void main() {
  vec2 uv = (gl_FragCoord.xy - uZone.xy) / uZone.zw;

  float fovV = min(FOV_H_MAX * uZone.w / uZone.z, FOV_V_MAX);
  float fovH = fovV * uZone.z / uZone.w;
  float azimut = uAzimutCentre + (uv.x - 0.5) * fovH;
  float hauteur = (uv.y - HORIZON) * fovV;

  // Repere local: y vers le zenith, x vers l'est, z vers le nord, l'azimut
  // etant compte depuis le nord vers l'est comme dans les donnees.
  vec3 dir = vec3(cos(hauteur) * sin(azimut), sin(hauteur), cos(hauteur) * cos(azimut));
  vec3 origine = positionObservateur();

  float versSol = intersectionSol(origine, dir);
  float portee = versSol > 0.0 ? versSol : intersectionSphere(origine, dir, R_ATMO);

  vec3 transmittance;
  vec3 lumiere = diffusion(origine, dir, portee, PAS, transmittance);
  if (versSol > 0.0) lumiere += transmittance * sol(origine + dir * versSol);

  sortie = vec4(versSRGB(tonalite(lumiere * EXPOSITION)), 1.0);
}`;
