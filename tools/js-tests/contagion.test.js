// tools/js-tests/contagion.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { correlation, sousEchantillon, deltaRelatif, correctionFR, analyse }
  from '../../assets/js/contagion/explorer.js';

const fix = JSON.parse(readFileSync(new URL('./fixture-contagion.json', import.meta.url)));
const donnees = JSON.parse(readFileSync(new URL('../../assets/data/contagion.json', import.meta.url)));

test('la correlation pleine periode reproduit Python a 1e-12', () => {
  const rho = correlation(donnees.rx, donnees.ry);
  assert.ok(Math.abs(rho - fix.rho_pleine) < 1e-12, `${rho} vs ${fix.rho_pleine}`);
});

test('chaque cas de fixture est reproduit: n, delta, rho, correction', () => {
  for (const cas of fix.cas) {
    const r = analyse(donnees.rx, donnees.ry, cas.q);
    assert.equal(r.n, cas.n, `n a q=${cas.q}`);
    for (const cle of ['delta', 'rho', 'rho_corrigee']) {
      assert.ok(Math.abs(r[cle] - cas[cle]) < 1e-12, `${cle} a q=${cas.q}: ${r[cle]} vs ${cas[cle]}`);
    }
  }
});

test('les briques sont coherentes entre elles', () => {
  const { rx, ry } = donnees;
  const [sx, sy] = sousEchantillon(rx, ry, 0.5);
  const delta = deltaRelatif(sx, rx);
  const rho = correlation(sx, sy);
  const r = analyse(rx, ry, 0.5);
  assert.equal(r.n, sx.length);
  assert.ok(Math.abs(correctionFR(rho, delta) - r.rho_corrigee) < 1e-15);
});
