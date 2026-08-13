// Miroir JavaScript de tools/eclipse/limb.py.
// Sert a construire la LUT flux <-> separation dans le navigateur, plutot que
// de l'embarquer dans le JSON. Le test tools/js-tests/flux.test.js verifie que
// ce fichier rend exactement les memes valeurs que Python: si les deux
// divergent, l'atmosphere et l'observateur ne sont plus eclaires par le meme
// Soleil, et rien ne le signalerait.
//
// L'ordre d'accumulation de la boucle doit rester identique a celui de Python:
// c'est une somme de flottants, donc le resultat en depend.

// Ordre (rouge, vert, bleu). Doit rester identique a limb.py.
export const SRGB_LIMB_COEFFS = [
  [0.37712, 0.27635], // rouge  610.975 nm
  [0.43044, 0.27494], // vert   552.200 nm
  [0.57264, 0.21241], // bleu   468.306 nm
];

// Dimensions de la LUT: separation d / r_soleil, puis rapport r_lune / r_soleil.
export const LUT_D = 256;
export const LUT_RATIO = 32;
export const RATIO_MIN = 0.90;
export const RATIO_MAX = 1.10;
export const D_MAX = 2.2;          // au-dela, la fraction vaut 1 par construction

export function intensity(mu, u1, u2) {
  const v = 1 - mu;
  return 1 - u1 * v - u2 * v * v;
}

export function visibleFluxFraction(d, rSun, rMoon, u1, u2, n = 512) {
  if (d >= rSun + rMoon) return 1;

  let total = 0;
  let visible = 0;
  for (let i = 0; i < n; i++) {
    const rho = ((i + 0.5) / n) * rSun;
    const mu = Math.sqrt(Math.max(0, 1 - (rho / rSun) ** 2));
    const poids = intensity(mu, u1, u2) * rho;
    total += poids;

    let fraction;
    if (d <= 0) {
      fraction = rho < rMoon ? 0 : 1;
    } else {
      const c = (rho * rho + d * d - rMoon * rMoon) / (2 * rho * d);
      if (c >= 1) fraction = 1;
      else if (c <= -1) fraction = 0;
      else fraction = 1 - Math.acos(c) / Math.PI;
    }
    visible += poids * fraction;
  }
  return visible / total;
}

// Construit la LUT flux <-> separation pour les trois canaux a la fois.
//
// Version naive: appeler visibleFluxFraction() trois fois par texel (une par
// canal) refait a chaque fois la meme geometrie d'anneau (rho, mu, acos), qui
// ne depend ni de u1 ni de u2 - seule la ponderation d'intensite en depend.
// Ici la geometrie de chaque anneau est calculee une seule fois, et les trois
// ponderations de canal sont appliquees dans cette meme boucle: l'acos et le
// sqrt ne sont donc plus faits qu'une fois par anneau au lieu de trois.
//
// Cela reste bit-identique a trois appels separes: pour un canal donne,
// l'accumulation de poids et de visible se fait toujours dans le meme ordre
// croissant de i que dans visibleFluxFraction. Seules trois sommes
// independantes sont menees de front dans une seule boucle - aucune d'elles
// n'est reordonnee.
export function buildFluxLut(n = 256) {
  const rSun = 1.0;
  const lut = new Float32Array(LUT_D * LUT_RATIO * 3);

  for (let j = 0; j < LUT_RATIO; j++) {
    const rMoon = RATIO_MIN + (RATIO_MAX - RATIO_MIN) * (j / (LUT_RATIO - 1));

    for (let i = 0; i < LUT_D; i++) {
      const d = (i / (LUT_D - 1)) * D_MAX;
      const base = (j * LUT_D + i) * 3;

      if (d >= rSun + rMoon) {
        lut[base] = 1;
        lut[base + 1] = 1;
        lut[base + 2] = 1;
        continue;
      }

      let total0 = 0, total1 = 0, total2 = 0;
      let visible0 = 0, visible1 = 0, visible2 = 0;

      for (let k = 0; k < n; k++) {
        const rho = ((k + 0.5) / n) * rSun;
        const mu = Math.sqrt(Math.max(0, 1 - (rho / rSun) ** 2));

        let fraction;
        if (d <= 0) {
          fraction = rho < rMoon ? 0 : 1;
        } else {
          const c = (rho * rho + d * d - rMoon * rMoon) / (2 * rho * d);
          if (c >= 1) fraction = 1;
          else if (c <= -1) fraction = 0;
          else fraction = 1 - Math.acos(c) / Math.PI;
        }

        const v = 1 - mu;
        const poids0 = (1 - SRGB_LIMB_COEFFS[0][0] * v - SRGB_LIMB_COEFFS[0][1] * v * v) * rho;
        const poids1 = (1 - SRGB_LIMB_COEFFS[1][0] * v - SRGB_LIMB_COEFFS[1][1] * v * v) * rho;
        const poids2 = (1 - SRGB_LIMB_COEFFS[2][0] * v - SRGB_LIMB_COEFFS[2][1] * v * v) * rho;

        total0 += poids0;
        total1 += poids1;
        total2 += poids2;
        visible0 += poids0 * fraction;
        visible1 += poids1 * fraction;
        visible2 += poids2 * fraction;
      }

      lut[base] = visible0 / total0;
      lut[base + 1] = visible1 / total1;
      lut[base + 2] = visible2 / total2;
    }
  }

  return lut;
}
