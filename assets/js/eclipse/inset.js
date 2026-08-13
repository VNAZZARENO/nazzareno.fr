// Encart teleobjectif d'un panneau. Meme contrat que sky.js: on lui donne un
// etat deja calcule et un rectangle de pixels, il dessine. Aucun DOM, aucune
// frise, et surtout AUCUN second canevas ni second contexte -- c'est une passe
// de plus sur le meme canevas, delimitee par le viewport et le ciseau.

import { createProgram, drawQuad } from './gl.js';
import { INSET_FS } from './inset.glsl.js';

const RAD = Math.PI / 180;

// Couleur du lisere, en sRGB. Un gris moyen neutre: l'encart s'appuie tantot
// sur un ciel de plein jour (clair), tantot sur le crepuscule de la totalite
// (sombre), et la page elle-meme existe en schema clair et en schema sombre.
// Une seule valeur doit donc tenir dans les quatre cas, et un gris a mi-chemin
// est la seule qui le fasse sans jamais disparaitre dans le fond.
const BORDURE = [0.55, 0.55, 0.57];

// Decalage angulaire vrai de la Lune par rapport au Soleil, projete dans le
// plan tangent a la direction du Soleil.
//
// C'est le seul calcul delicat de ce module, et le faire a la legere donnerait
// une geometrie fausse. Une difference d'azimut n'est PAS un angle sur le
// ciel: a la hauteur h, un degre d'azimut ne vaut que cos(h) degres. A Palma
// le Soleil est a 2,6 deg de hauteur et l'erreur serait negligeable, mais a
// Reykjavik il est a 24,5 deg et la separation serait surestimee de 10 % --
// assez pour que l'encart montre une totalite plus large qu'elle n'est, ou
// pas de totalite du tout.
//
// Plutot que d'appliquer un facteur cos(h) a la main, on projette le vecteur
// unitaire de la Lune sur la base orthonormee (est, zenith local) du plan
// tangent au Soleil. Le cos(h) en sort tout seul -- dot(lune, est) vaut
// cos(h_lune) sin(az_lune - az_soleil) -- et la formule reste exacte quelle
// que soit la hauteur, sans cas particulier.
//
// Verification faite sur les donnees: la magnitude reconstruite depuis cette
// separation, (rSun + rMoon - separation) / (2 rSun), reproduit la magnitude
// publiee dans le JSON a 6e-5 pres pour les trois lieux, a leur maximum. Si
// l'encart et les chiffres divergeaient, c'est ici qu'il faudrait chercher.
export function decalageLune(etat) {
  const az = etat.sunAz * RAD;
  const alt = etat.sunAlt * RAD;
  const azLune = etat.moonAz * RAD;
  const altLune = etat.moonAlt * RAD;

  // Repere du ciel: y vers le zenith, x vers l'est, z vers le nord -- le meme
  // que sky.js, azimut compte depuis le nord vers l'est.
  const lune = [
    Math.cos(altLune) * Math.sin(azLune),
    Math.sin(altLune),
    Math.cos(altLune) * Math.cos(azLune),
  ];
  // Est local au Soleil (derivee de sa direction par l'azimut, normalisee) et
  // zenith local (derivee par la hauteur, deja unitaire).
  const est = [Math.cos(az), 0, -Math.sin(az)];
  const haut = [-Math.sin(alt) * Math.sin(az), Math.cos(alt), -Math.sin(alt) * Math.cos(az)];

  const projeter = (base) => lune[0] * base[0] + lune[1] * base[1] + lune[2] * base[2];
  return [projeter(est), projeter(haut)];
}

// `etat` attend les memes champs que sky.js, aux memes unites (degres):
// sunAz, sunAlt, moonAz, moonAlt, rSun, rMoon, fluxR/G/B.
// `zone` = { x, y, w, h } en pixels de la memoire tampon, origine en bas a
// gauche, exactement comme gl.viewport.
export function createInset(gl) {
  const programme = createProgram(gl, INSET_FS, 'encart');
  const lieu = (nom) => gl.getUniformLocation(programme, nom);
  const u = {
    zone: lieu('uZone'),
    lune: lieu('uLune'),
    rSoleil: lieu('uRSoleil'),
    rLune: lieu('uRLune'),
    flux: lieu('uFlux'),
    bordure: lieu('uBordure'),
  };

  return function dessinerEncart(etat, zone) {
    const [dx, dy] = decalageLune(etat);

    // Le ciseau est obligatoire: le triangle plein cadre de gl.js deborde le
    // viewport, et sans lui l'encart effacerait le panneau qui le porte.
    gl.viewport(zone.x, zone.y, zone.w, zone.h);
    gl.scissor(zone.x, zone.y, zone.w, zone.h);
    gl.enable(gl.SCISSOR_TEST);

    gl.useProgram(programme);
    gl.uniform4f(u.zone, zone.x, zone.y, zone.w, zone.h);
    gl.uniform2f(u.lune, dx, dy);
    // Rayons apparents en radians, comme dans sky.js: le shader ne travaille
    // qu'en angles, jamais en degres.
    gl.uniform1f(u.rSoleil, etat.rSun * RAD);
    gl.uniform1f(u.rLune, etat.rMoon * RAD);
    gl.uniform3f(u.flux, etat.fluxR, etat.fluxG, etat.fluxB);
    gl.uniform3f(u.bordure, BORDURE[0], BORDURE[1], BORDURE[2]);

    drawQuad(gl);

    // On rend le contexte comme on l'a trouve, meme convention que sky.js.
    gl.disable(gl.SCISSOR_TEST);
  };
}
