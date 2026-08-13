// Construction des LUT d'atmosphere. Elles sont INDEPENDANTES DU LIEU: la
// transmittance ne depend que de l'altitude et de l'angle zenithal, la
// diffusion multiple que de l'altitude et de la hauteur du Soleil, la LUT de
// flux que de la geometrie des deux disques. On les calcule donc une seule
// fois, et les deux panneaux les partagent.

import {
  createProgram, drawQuad, createTexture, renderToTexture, RGBA16F, RGB32F,
} from './gl.js';
import { ATMOSPHERE, TRANSMITTANCE_LUT } from './atmosphere.glsl.js';
import { buildFluxLut, LUT_D, LUT_RATIO } from './flux.js';

export const TRANSMITTANCE_L = 256;   // axe x: cosinus de l'angle zenithal
export const TRANSMITTANCE_H = 64;    // axe y: altitude, du sol au sommet

export const MULTISCATTER_L = 32;     // axe x: cosinus zenithal DU SOLEIL
export const MULTISCATTER_H = 32;     // axe y: altitude, du sol au sommet

// Transmittance du point de vue jusqu'au sommet de l'atmosphere.
// Parametrage: x -> cosZenith dans [-1, 1], y -> altitude dans [0, R_ATMO - R_SOL].
// Une visee rasante ou plongeante traverse le sol: on borne alors l'altitude a
// zero, ce qui rend une epaisseur optique enorme et donc une transmittance
// nulle -- exactement ce qu'on veut, le sol est opaque.
const FS_TRANSMITTANCE = `#version 300 es
precision highp float;
out vec4 sortie;
uniform vec2 uTaille;
${ATMOSPHERE}

const int PAS = 40;

void main() {
  vec2 uv = gl_FragCoord.xy / uTaille;
  float altitude = uv.y * (R_ATMO - R_SOL);
  float cosZenith = uv.x * 2.0 - 1.0;

  vec3 p = vec3(0.0, R_SOL + altitude, 0.0);
  vec3 dir = vec3(sqrt(max(0.0, 1.0 - cosZenith * cosZenith)), cosZenith, 0.0);

  float parcours = intersectionSphere(p, dir, R_ATMO);
  float dt = parcours / float(PAS);

  vec3 optique = vec3(0.0);
  for (int i = 0; i < PAS; i++) {
    float t = (float(i) + 0.5) * dt;
    float h = length(p + dir * t) - R_SOL;
    optique += extinction(max(h, 0.0)) * dt;
  }
  sortie = vec4(exp(-optique), 1.0);
}`;

// Diffusion multiple, dans la forme de Hillaire (2020, section 4.3).
//
// La diffusion simple seule rend un ciel trop sombre et de la mauvaise couleur:
// dans l'atmosphere reelle la luminance du ciel est a peu pres doublee par la
// lumiere qui a rebondi plus d'une fois, et le bleu profond du crepuscule est
// en grande partie un effet de diffusion multiple. La tache 17 en avait mesure
// le symptome: a Soleil haut, le sol rendait PLUS clair que le ciel, ce qui est
// faux.
//
// Le principe est une serie geometrique. On calcule d'abord L2, la lumiere
// diffusee une seconde fois vers le point, en integrant sur une sphere de
// directions la diffusion simple vue depuis ce point. On calcule ensuite f, la
// fraction d'une luminance ambiante UNITE que le meme voisinage rediffuse vers
// le point. Chaque ordre suivant vaut alors f fois le precedent, et la somme
// de tous les ordres vaut L2 * (1 + f + f^2 + ...) = L2 / (1 - f).
//
// Deux approximations, assumees, qui sont celles de l'article: la phase est
// prise isotrope au-dela du premier rebond (au troisieme rebond la lumiere a
// perdu la memoire de sa direction), et l'atmosphere est supposee localement
// homogene autour du point echantillonne -- d'ou une table a deux entrees
// seulement, et 32x32 texels suffisent pour un champ aussi lisse.
const FS_MULTISCATTER = `#version 300 es
precision highp float;
precision highp sampler2D;
out vec4 sortie;
uniform vec2 uTaille;
${ATMOSPHERE}
${TRANSMITTANCE_LUT}

const int DIRECTIONS = 64;      // sphere de directions, spirale de Fibonacci
const int PAS = 20;             // pas du raymarch secondaire
const float PHASE_ISOTROPE = 1.0 / (4.0 * PI);

void main() {
  vec2 uv = gl_FragCoord.xy / uTaille;
  float altitude = uv.y * (R_ATMO - R_SOL);
  float cosSoleil = uv.x * 2.0 - 1.0;

  vec3 origine = vec3(0.0, R_SOL + altitude, 0.0);
  vec3 soleil = vec3(sqrt(max(0.0, 1.0 - cosSoleil * cosSoleil)), cosSoleil, 0.0);

  vec3 ordre2 = vec3(0.0);
  vec3 transfert = vec3(0.0);

  for (int i = 0; i < DIRECTIONS; i++) {
    // Spirale de Fibonacci: 64 directions quasi uniformes sur la sphere, sans
    // generateur aleatoire et donc sans bruit d'une texel a l'autre.
    float k = (float(i) + 0.5) / float(DIRECTIONS);
    float cosT = 1.0 - 2.0 * k;
    float sinT = sqrt(max(0.0, 1.0 - cosT * cosT));
    float phi = float(i) * 2.39996323;   // angle d'or, en radians
    // y est le zenith dans ce repere: c'est cosT qui porte l'angle zenithal.
    vec3 dir = vec3(sinT * cos(phi), cosT, sinT * sin(phi));

    float versSol = intersectionSol(origine, dir);
    float portee = versSol > 0.0 ? versSol : intersectionSphere(origine, dir, R_ATMO);
    float dt = portee / float(PAS);

    vec3 lumiere = vec3(0.0);
    vec3 apport = vec3(0.0);
    vec3 debit = vec3(1.0);

    for (int j = 0; j < PAS; j++) {
      vec3 p = origine + dir * ((float(j) + 0.5) * dt);
      float h = max(0.0, length(p) - R_SOL);
      vec3 sigmaS = diffusionTotale(h);
      vec3 sigmaE = max(extinction(h), vec3(1e-9));
      vec3 attenuation = exp(-sigmaE * dt);

      // Meme integration analytique du pas que le raymarch du ciel.
      vec3 source = transmittanceVers(h, dot(normalize(p), soleil))
                  * sigmaS * PHASE_ISOTROPE;
      lumiere += debit * (source - source * attenuation) / sigmaE;
      // Le meme calcul avec une luminance incidente egale a 1 partout: c'est
      // la fraction f qui alimente la serie geometrique.
      apport += debit * (sigmaS - sigmaS * attenuation) / sigmaE;
      debit *= attenuation;
    }

    // Rebond lambertien sur le sol, avec l'albedo du sol qu'on dessine. Le sol
    // renvoie du Soleil (terme d'ordre 2) et renvoie aussi l'ambiante (terme
    // de transfert): il compte donc dans les deux sommes, sans quoi la serie
    // oublierait qu'une eclaireuse de plus existe sous l'atmosphere.
    if (versSol > 0.0) {
      vec3 n = normalize(origine + dir * versSol);
      float cosSol = dot(n, soleil);
      if (cosSol > 0.0) {
        lumiere += debit * ALBEDO_SOL / PI * cosSol * transmittanceVers(0.0, cosSol);
      }
      apport += debit * ALBEDO_SOL;
    }

    ordre2 += lumiere;
    transfert += apport;
  }

  // L'integrale sur la sphere vaut 4*PI * moyenne, et la phase isotrope vaut
  // 1/(4*PI): les deux se compensent, il ne reste que la moyenne.
  ordre2 /= float(DIRECTIONS);
  transfert /= float(DIRECTIONS);

  // f < 1 physiquement (l'atmosphere absorbe); la borne n'est la que pour
  // qu'une erreur numerique ne puisse pas produire un infini.
  sortie = vec4(ordre2 / max(vec3(1.0) - transfert, vec3(1e-3)), 1.0);
}`;

// Construit les tables et rend les textures. `gl` vient de createContext, donc
// EXT_color_buffer_float est deja garantie: la cible RGBA16F est rendable.
export function buildLuts(gl) {
  const transmittance = createTexture(gl, TRANSMITTANCE_L, TRANSMITTANCE_H, RGBA16F(gl));
  const programme = createProgram(gl, FS_TRANSMITTANCE, 'transmittance');
  renderToTexture(gl, transmittance, TRANSMITTANCE_L, TRANSMITTANCE_H, () => {
    gl.useProgram(programme);
    gl.uniform2f(
      gl.getUniformLocation(programme, 'uTaille'),
      TRANSMITTANCE_L, TRANSMITTANCE_H,
    );
    drawQuad(gl);
  });
  gl.deleteProgram(programme);

  // La diffusion multiple lit la transmittance: elle se construit donc APRES,
  // et jamais avant.
  const multiscatter = createTexture(gl, MULTISCATTER_L, MULTISCATTER_H, RGBA16F(gl));
  const programmeMS = createProgram(gl, FS_MULTISCATTER, 'diffusion-multiple');
  renderToTexture(gl, multiscatter, MULTISCATTER_L, MULTISCATTER_H, () => {
    gl.useProgram(programmeMS);
    gl.uniform2f(
      gl.getUniformLocation(programmeMS, 'uTaille'),
      MULTISCATTER_L, MULTISCATTER_H,
    );
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, transmittance);
    gl.uniform1i(gl.getUniformLocation(programmeMS, 'uTransmittance'), 0);
    drawQuad(gl);
  });
  gl.deleteProgram(programmeMS);

  // La LUT flux <-> separation est calculee au CPU (flux.js, miroir de
  // limb.py) puis simplement televersee: aucun shader n'a besoin de la
  // reconstruire, et c'est le meme modele que celui valide par les tests.
  const flux = createTexture(gl, LUT_D, LUT_RATIO, RGB32F(gl), buildFluxLut());

  return { transmittance, multiscatter, flux };
}
