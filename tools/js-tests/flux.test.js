import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { visibleFluxFraction, buildFluxLut, SRGB_LIMB_COEFFS, LUT_D, LUT_RATIO }
  from '../../assets/js/eclipse/flux.js';

const ref = JSON.parse(readFileSync(new URL('./flux-reference.json', import.meta.url)));

test('les coefficients JS sont identiques a ceux de Python', () => {
  assert.deepEqual(SRGB_LIMB_COEFFS.map((c) => [...c]), ref.coeffs);
});

test('le JS reproduit Python a 1e-9 pres', () => {
  for (const cas of ref.cases) {
    for (let c = 0; c < 3; c++) {
      const [u1, u2] = ref.coeffs[c];
      const obtenu = visibleFluxFraction(cas.d, 1.0, cas.rMoon, u1, u2, ref.n);
      assert.ok(Math.abs(obtenu - cas.flux[c]) < 1e-9,
        `d=${cas.d} rMoon=${cas.rMoon} canal=${c}: ${obtenu} vs ${cas.flux[c]}`);
    }
  }
});

test('la LUT a la bonne taille et reste dans [0, 1]', () => {
  const lut = buildFluxLut();
  assert.equal(lut.length, LUT_D * LUT_RATIO * 3);
  assert.ok(lut.every((v) => v >= 0 && v <= 1));
});

test('la LUT vaut 1 a separation maximale et 0 en totalite centrale', () => {
  const lut = buildFluxLut();
  const idx = (i, j, c) => (j * LUT_D + i) * 3 + c;
  assert.ok(lut[idx(LUT_D - 1, LUT_RATIO - 1, 1)] > 0.999);
  assert.ok(lut[idx(0, LUT_RATIO - 1, 1)] < 1e-6);
});
