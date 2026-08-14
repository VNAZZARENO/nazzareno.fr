// assets/js/contagion/ui.js
// L'enveloppe DOM de l'explorateur: chargement du JSON, curseur, affichage.
// Tout le calcul est dans explorer.js, teste sous node; ici il n'y a que la page.
import { analyse, correlation } from './explorer.js';

const bloc = document.getElementById('explorateur');
if (bloc) init().catch(() => { /* sans donnees, le noscript et la figure suffisent */ });

async function init() {
  const reponse = await fetch('/assets/data/contagion.json');
  if (!reponse.ok) return;
  const { rx, ry } = await reponse.json();
  const pleine = correlation(rx, ry);
  const fr = document.documentElement.lang === 'fr';
  const nombre = (v, dec) => fr ? v.toFixed(dec).replace('.', ',') : v.toFixed(dec);

  // Si le balisage n'est pas complet on ne cable rien: mieux vaut aucun
  // encart qu'une moitie d'encart (convention de l'eclipse).
  const curseur = document.getElementById('explo-seuil');
  const sortieQ = document.getElementById('explo-q');
  const valeurs = document.getElementById('explo-valeurs');
  const barres = {
    brute: bloc.querySelector('.explo-barre.explo-a'),
    corrigee: bloc.querySelector('.explo-barre.explo-b'),
  };
  if (!curseur || !sortieQ || !valeurs || !barres.brute || !barres.corrigee) return;

  // le curseur est a pas fixes: tout precalculer une fois coute ~25 ms hors
  // interaction, et l'ecoute d'input ne fait plus qu'indexer.
  const resultats = new Map();
  for (let v = Number(curseur.min); v <= Number(curseur.max); v += Number(curseur.step)) {
    resultats.set(v, analyse(rx, ry, v / 100));
  }

  // le repere de pleine periode, une fine ligne posee au meme endroit sur les
  // deux pistes: c'est la reference que la brute quitte et que la corrigee garde.
  for (const piste of bloc.querySelectorAll('.explo-piste')) {
    const repere = document.createElement('div');
    repere.className = 'explo-repere';
    repere.style.left = `${pleine * 100}%`;
    piste.append(repere);
  }

  function rendre() {
    const r = resultats.get(Number(curseur.value));
    if (!r) return;
    sortieQ.textContent = nombre(Number(curseur.value) / 100, 2);
    barres.brute.style.width = `${Math.max(0, r.rho) * 100}%`;
    barres.corrigee.style.width = `${Math.max(0, r.rho_corrigee) * 100}%`;
    const texte = fr
      ? `${r.n} jours gardés · δ = ${nombre(r.delta, 2)} · brute ${nombre(r.rho, 3)} · corrigée ${nombre(r.rho_corrigee, 3)} · pleine période ${nombre(pleine, 3)}`
      : `${r.n} days kept · δ = ${nombre(r.delta, 2)} · raw ${nombre(r.rho, 3)} · corrected ${nombre(r.rho_corrigee, 3)} · full sample ${nombre(pleine, 3)}`;
    // aria-live reannonce a chaque ecriture, meme identique: on ne touche au
    // noeud que si la valeur a change. Le curseur etant a pas de 5, les
    // annonces restent naturellement rares, pas besoin d'un minuteur.
    if (valeurs.textContent !== texte) valeurs.textContent = texte;
  }

  curseur.addEventListener('input', rendre);
  rendre();
  bloc.hidden = false;
}
