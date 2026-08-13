// Construction des LUT d'atmosphere. Elles sont INDEPENDANTES DU LIEU: la
// transmittance ne depend que de l'altitude et de l'angle zenithal, la LUT de
// flux ne depend que de la geometrie des deux disques. On les calcule donc une
// seule fois, et les deux panneaux les partagent.

import {
  createProgram, drawQuad, createTexture, renderToTexture, RGBA16F, RGB32F,
} from './gl.js';
import { ATMOSPHERE } from './atmosphere.glsl.js';
import { buildFluxLut, LUT_D, LUT_RATIO } from './flux.js';

export const TRANSMITTANCE_L = 256;   // axe x: cosinus de l'angle zenithal
export const TRANSMITTANCE_H = 64;    // axe y: altitude, du sol au sommet

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

  // La LUT flux <-> separation est calculee au CPU (flux.js, miroir de
  // limb.py) puis simplement televersee: aucun shader n'a besoin de la
  // reconstruire, et c'est le meme modele que celui valide par les tests.
  const flux = createTexture(gl, LUT_D, LUT_RATIO, RGB32F(gl), buildFluxLut());

  return { transmittance, flux };
}
