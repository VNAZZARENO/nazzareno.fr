// Fragments GLSL partages entre la construction des LUT et le rendu du ciel.
// Regrouper ces definitions ici garantit que la LUT de transmittance et le
// raymarch utilisent exactement les memes densites: si elles divergeaient, le
// ciel serait faux d'une maniere tres difficile a diagnostiquer -- l'image
// resterait plausible, seulement fausse.
//
// Les coefficients sont les valeurs standard pour la Terre du modele de
// Bruneton & Neyret (2008), telles que reprises par Hillaire, "A Scalable and
// Production Ready Sky and Atmosphere Rendering Technique" (EGSR 2020). Ils
// sont donnes en m^-1 au niveau de la mer, pour trois longueurs d'onde
// representatives des canaux sRGB. Ce ne sont donc pas des nombres magiques
// ajustes a l'oeil: ils sont tracables, et on ne les retouche pas pour
// "arranger" une image.

export const ATMOSPHERE = `
const float PI = 3.14159265;

const float R_SOL = 6360000.0;      // rayon de la planete, en metres
const float R_ATMO = 6460000.0;     // sommet de l'atmosphere

// Albedo du sol. Il vit ici et pas dans le shader du ciel parce que la LUT de
// diffusion multiple en a besoin elle aussi: la lumiere qui rebondit sur le sol
// est une part non negligeable de ce qui revient au ciel. Deux valeurs
// divergentes donneraient un ciel eclaire par un sol qui n'est pas celui qu'on
// dessine.
const float ALBEDO_SOL = 0.10;

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

// Densites relatives (rayleigh, mie, ozone) a une altitude donnee, en metres.
// Rayleigh et Mie decroissent exponentiellement; l'ozone suit sa couche.
vec3 densites(float altitude) {
  float rayleigh = exp(-altitude / H_RAYLEIGH);
  float mie = exp(-altitude / H_MIE);
  float ozone = max(0.0, 1.0 - abs(altitude - 25000.0) / 15000.0);
  return vec3(rayleigh, mie, ozone);
}

// Coefficient d'extinction total, par canal: diffusion Rayleigh, diffusion
// ET absorption de Mie, absorption de l'ozone (qui ne diffuse pas).
vec3 extinction(float altitude) {
  vec3 d = densites(altitude);
  return BETA_RAYLEIGH * d.x
       + (BETA_MIE + BETA_MIE_ABSORPTION) * d.y
       + BETA_OZONE * d.z;
}

// Coefficient de DIFFUSION seul (sans les termes d'absorption), par canal.
// C'est lui qui module la diffusion multiple: l'ozone et l'absorption de Mie
// eteignent la lumiere mais n'en renvoient aucune.
vec3 diffusionTotale(float altitude) {
  vec3 d = densites(altitude);
  return BETA_RAYLEIGH * d.x + BETA_MIE * d.y;
}

float phaseRayleigh(float cosTheta) {
  return 3.0 / (16.0 * PI) * (1.0 + cosTheta * cosTheta);
}

// Henyey-Greenstein sous la forme de Cornette-Shanks, qui reste normalisee et
// evite le pic trop dur du HG brut vers l'avant.
float phaseMie(float cosTheta) {
  float g = G_MIE;
  float g2 = g * g;
  float d = 1.0 + g2 - 2.0 * g * cosTheta;
  return 3.0 / (8.0 * PI) * ((1.0 - g2) * (1.0 + cosTheta * cosTheta))
       / ((2.0 + g2) * pow(max(d, 1e-4), 1.5));
}

// Distance du point p a la sortie de la sphere de rayon r centree sur
// l'origine, dans la direction dir (supposee normalisee). Rend -1 si le rayon
// manque la sphere.
float intersectionSphere(vec3 p, vec3 dir, float r) {
  float b = dot(p, dir);
  float c = dot(p, p) - r * r;
  float disc = b * b - c;
  if (disc < 0.0) return -1.0;
  return -b + sqrt(disc);
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
`;

// Lecture de la LUT de transmittance. Ce fragment est separe d'ATMOSPHERE
// parce qu'il declare un uniform: seuls les shaders qui echantillonnent la
// table l'incluent (le shader qui la CONSTRUIT, lui, n'en a evidemment pas
// besoin). Le parametrage vit ici et nulle part ailleurs -- construction et
// lecture ne peuvent donc pas diverger d'un demi-texel sans qu'on le voie.
export const TRANSMITTANCE_LUT = `
uniform sampler2D uTransmittance;

// Transmittance depuis un point d'altitude alt jusqu'au sommet de
// l'atmosphere, dans la direction de cosinus zenithal cosZenith. Le
// parametrage est exactement celui de luts.js: x = (cosZenith + 1) / 2,
// y = alt / (R_ATMO - R_SOL). Les visees plongeantes traversent le sol et la
// LUT y rend une transmittance nulle -- l'ombre de la planete est gratuite.
vec3 transmittanceVers(float alt, float cosZenith) {
  vec2 uv = vec2(cosZenith * 0.5 + 0.5, alt / (R_ATMO - R_SOL));
  return texture(uTransmittance, clamp(uv, 0.0, 1.0)).rgb;
}
`;
