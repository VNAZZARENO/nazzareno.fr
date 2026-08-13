// Fragment shader du ciel: diffusion simple, en projection equidistante.
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
//    transmittance vers le Soleil est lue dans la LUT plutot que marchee. Un
//    rayon secondaire par pas couterait 32 fois plus cher pour une image que
//    personne ne saurait distinguer.
//
// 3. L'exposition est FIXE. Pas d'auto-exposition, pas d'adaptation
//    temporelle. La page montrera deux lieux cote a cote et le sujet meme de
//    la page est que l'un s'assombrit et pas l'autre: une auto-exposition
//    relevrait le lieu sombre et effacerait exactement ce qu'il y a a voir.

import { ATMOSPHERE } from './atmosphere.glsl.js';

// Exposition FIXE, calibree une fois pour toutes. L'ancrage est le sol
// ensoleille au zenith -- albedo 0.10, eclaire par le Soleil direct -- qu'on
// place vers un gris moyen (sRGB 0.60 environ). On ancre volontairement sur ce
// terme-la et pas sur le ciel: le Soleil direct est deja exact, alors que la
// luminance du ciel augmentera encore quand la diffusion multiple arrivera
// (tache 19). Calibrer sur le ciel obligerait a tout redecaler ensuite.
// A 40, le plein jour ne sature nulle part (0 % de pixels ecretes de 0 a 60
// degres de hauteur solaire) et il reste de la marge pour cet apport a venir.
// Les unites sont arbitraires: l'irradiance solaire hors atmosphere vaut 1 par
// canal, donc ce nombre n'a de sens que relativement a elle.
const EXPOSITION = 40.0;

export const SKY_FS = `#version 300 es
precision highp float;
precision highp sampler2D;
out vec4 sortie;

uniform vec4 uZone;             // x, y, largeur, hauteur du panneau, en pixels
uniform vec3 uSoleil;           // direction unitaire vers le Soleil
uniform vec3 uFlux;             // flux solaire visible par canal (1 = disque entier)
uniform float uAzimutCentre;    // azimut vise au centre du panneau, en radians
uniform float uAltitudeObs;     // altitude de l'observateur, en metres
uniform sampler2D uTransmittance;

${ATMOSPHERE}

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
const float ALBEDO_SOL = 0.10;
const float EXPOSITION = ${EXPOSITION.toFixed(1)};
const float PI = 3.14159265;

// Transmittance depuis un point d'altitude alt jusqu'au sommet de
// l'atmosphere, dans la direction de cosinus zenithal cosZenith. Le
// parametrage est exactement celui de luts.js: x = (cosZenith + 1) / 2,
// y = alt / (R_ATMO - R_SOL). Les visees plongeantes traversent le sol et la
// LUT y rend une transmittance nulle -- l'ombre de la planete est gratuite.
vec3 transmittanceVers(float alt, float cosZenith) {
  vec2 uv = vec2(cosZenith * 0.5 + 0.5, alt / (R_ATMO - R_SOL));
  return texture(uTransmittance, clamp(uv, 0.0, 1.0)).rgb;
}

// Distance a la PREMIERE intersection avec le sol, ou -1 si le rayon le
// manque. intersectionSphere ne rend que la racine lointaine, celle qui sert au
// sommet de l'atmosphere; pour le sol c'est l'entree qu'on veut.
float intersectionSol(vec3 p, vec3 dir) {
  float b = dot(p, dir);
  float c = dot(p, p) - R_SOL * R_SOL;
  float disc = b * b - c;
  if (disc < 0.0) return -1.0;
  float t = -b - sqrt(disc);
  return t > 0.0 ? t : -1.0;
}

// Diffusion simple le long d'un rayon. Rend la lumiere diffusee vers
// l'observateur, et par transmittance l'attenuation totale du rayon -- c'est
// elle qui donne la perspective aerienne quand le rayon finit au sol.
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
    vec3 sigmaS = BETA_RAYLEIGH * d.x * phaseR + BETA_MIE * d.y * phaseM;
    vec3 versSoleil = transmittanceVers(h, dot(normalize(p), uSoleil));

    // Integration analytique de la diffusion sur le pas (Hillaire 2020):
    // exacte a extinction constante sur le segment, elle supprime le banding
    // qu'une simple somme au point milieu laisse voir dans les degrades.
    vec3 attenuation = exp(-sigmaE * dt);
    vec3 apport = (sigmaS - sigmaS * attenuation) / sigmaE;
    lumiere += transmittance * apport * versSoleil * uFlux;
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
  vec3 direct = transmittanceVers(0.0, cosSoleil) * max(cosSoleil, 0.0) * uFlux;

  // Eclairement du ciel, approxime au premier ordre par un ciel uniforme ayant
  // la luminance du zenith: E = pi * L. Le sol ne merite pas une integrale
  // d'hemisphere par pixel, mais il lui faut cet apport: sans lui, tout ce qui
  // n'est pas au soleil devient un noir plat, ce qui est faux.
  vec3 ignore;
  vec3 zenith = diffusion(p + n, n, R_ATMO - R_SOL, PAS_AMBIANT, ignore);

  return ALBEDO_SOL / PI * (direct + PI * zenith);
}

// Courbe filmique de Hable ("Uncharted 2"), retenue pour son pied souple: elle
// releve les ombres et comprime les hautes lumieres. C'est elle qui tient ici
// le role de la reponse a peu pres logarithmique de l'oeil, que l'exposition
// fixe ne peut pas rendre.
vec3 hable(vec3 x) {
  const float A = 0.15, B = 0.50, C = 0.10, D = 0.20, E = 0.02, F = 0.30;
  return ((x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F)) - E / F;
}

vec3 tonalite(vec3 lumiere) {
  return hable(lumiere) / hable(vec3(11.2));
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
  vec3 origine = vec3(0.0, R_SOL + uAltitudeObs, 0.0);

  float versSol = intersectionSol(origine, dir);
  float portee = versSol > 0.0 ? versSol : intersectionSphere(origine, dir, R_ATMO);

  vec3 transmittance;
  vec3 lumiere = diffusion(origine, dir, portee, PAS, transmittance);
  if (versSol > 0.0) lumiere += transmittance * sol(origine + dir * versSol);

  sortie = vec4(versSRGB(tonalite(lumiere * EXPOSITION)), 1.0);
}`;
