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
const float R_SOL = 6360000.0;      // rayon de la planete, en metres
const float R_ATMO = 6460000.0;     // sommet de l'atmosphere

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

float phaseRayleigh(float cosTheta) {
  return 3.0 / (16.0 * 3.14159265) * (1.0 + cosTheta * cosTheta);
}

// Henyey-Greenstein sous la forme de Cornette-Shanks, qui reste normalisee et
// evite le pic trop dur du HG brut vers l'avant.
float phaseMie(float cosTheta) {
  float g = G_MIE;
  float g2 = g * g;
  float d = 1.0 + g2 - 2.0 * g * cosTheta;
  return 3.0 / (8.0 * 3.14159265) * ((1.0 - g2) * (1.0 + cosTheta * cosTheta))
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
`;
