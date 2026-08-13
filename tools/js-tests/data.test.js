import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseEclipse, stateAt, windowSeconds } from '../../assets/js/eclipse/data.js';

const brut = JSON.parse(readFileSync(new URL('./fixture-eclipse.json', import.meta.url)));
const eclipse = parseEclipse(brut);
const site = eclipse.sites[0];

test('la fenetre couvre toutes les images', () => {
  assert.equal(windowSeconds(site), 40);
});

test('rend exactement la premiere image a t = 0', () => {
  const e = stateAt(site, 0);
  assert.equal(e.sunAlt, 30);
  assert.equal(e.fluxG, 1);
});

test('rend exactement la derniere image en fin de fenetre', () => {
  const e = stateAt(site, 40);
  assert.equal(e.sunAlt, 34);
  assert.equal(e.fluxG, 0);
});

test('interpole lineairement entre deux images', () => {
  const e = stateAt(site, 10);
  assert.equal(e.sunAlt, 31);
  assert.equal(e.fluxG, 0.75);
});

test("l'azimut prend le chemin le plus court a travers zero", () => {
  // de 20 deg a 350 deg: le chemin court passe par 5 deg, pas par 185 deg
  const e = stateAt(site, 30);
  assert.equal(e.sunAz, 5);
});

test('borne les temps hors fenetre au lieu d extrapoler', () => {
  assert.equal(stateAt(site, -100).sunAlt, 30);
  assert.equal(stateAt(site, 1e6).sunAlt, 34);
});

test('les contacts sont deja en secondes depuis t0', () => {
  assert.equal(site.contacts.c1, 0);
  assert.equal(site.contacts.c4, 40);
  assert.equal(site.contacts.c2, null);
});
