// Rendu d'un panneau de ciel. Ce module ne connait ni la frise, ni le DOM, ni
// les commandes: on lui donne un etat deja calcule, un rectangle de pixels et
// les LUT, il dessine. C'est ce qui permettra a la tache 20 de l'appeler deux
// fois par image, pour deux lieux, sans rien dupliquer.

import { createProgram, drawQuad } from './gl.js';
import { SKY_FS, MAX_ASTRES } from './sky.glsl.js';

const RAD = Math.PI / 180;

// Magnitudes apparentes des planetes. Le JSON (sky_at_max) porte leur azimut
// et leur hauteur, calcules par les ephemerides JPL, mais PAS de magnitude:
// contrairement aux etoiles Hipparcos, ce n'est pas une donnee du catalogue
// d'entree de la tache 7. Les valeurs ci-dessous sont une STYLISATION
// deliberee -- des ordres de grandeur plausibles pour aout 2026 (Venus tres
// brillante, Mars discrete), choisis pour que le ciel ait l'air juste, pas
// calcules depuis une ephemeride de luminosite. Si une planete manque a cette
// table, MAGNITUDE_PLANETE_DEFAUT s'applique.
const MAGNITUDE_PLANETE = {
  Mercure: 0.3,
  Venus: -4.4,
  Mars: 1.6,
  Jupiter: -2.1,
  Saturne: 0.7,
};
const MAGNITUDE_PLANETE_DEFAUT = 1.0;

// Cache par objet sky_at_max: cette donnee ne change jamais apres le
// chargement du JSON (elle est figee a l'instant du maximum, voir le
// commentaire de sky.glsl.js), donc la reconstruire a chaque image serait un
// aller-retour pour rien. La cle est l'objet lui-meme -- il n'existe qu'une
// instance par site -- donc changer de lieu invalide le cache tout seul, sans
// qu'il faille l'invalider a la main.
const cacheAstres = new WeakMap();

// Assemble planetes puis etoiles (deja triees par magnitude croissante --
// donc de la plus brillante a la plus faible -- par la tache 7) en un seul
// Float32Array plat de MAX_ASTRES triples (azimut, hauteur en RADIANS,
// magnitude). Avec jusqu'a 60 etoiles ET jusqu'a 4 planetes selon le lieu, la
// somme deborde MAX_ASTRES: les planetes passent en premier, toujours parmi
// les objets les plus brillants du ciel, puis les etoiles les plus brillantes
// comblent le reste. Ce sont donc les etoiles les plus FAIBLES qui sont
// sacrifiees en cas de depassement, jamais une planete.
function construireAstres(skyAtMax) {
  const planetes = skyAtMax.planets ?? [];
  const etoiles = skyAtMax.stars ?? [];
  const tableau = new Float32Array(MAX_ASTRES * 3);
  let n = 0;
  for (let i = 0; i < planetes.length && n < MAX_ASTRES; i++) {
    const p = planetes[i];
    const mag = MAGNITUDE_PLANETE[p.name] ?? MAGNITUDE_PLANETE_DEFAUT;
    tableau[n * 3] = p.az * RAD;
    tableau[n * 3 + 1] = p.alt * RAD;
    tableau[n * 3 + 2] = mag;
    n++;
  }
  for (let i = 0; i < etoiles.length && n < MAX_ASTRES; i++) {
    const e = etoiles[i];
    tableau[n * 3] = e.az * RAD;
    tableau[n * 3 + 1] = e.alt * RAD;
    tableau[n * 3 + 2] = e.mag;
    n++;
  }
  return { tableau, n };
}

function astresDuSite(skyAtMax) {
  if (!skyAtMax) return { tableau: null, n: 0 };
  let entree = cacheAstres.get(skyAtMax);
  if (!entree) {
    entree = construireAstres(skyAtMax);
    cacheAstres.set(skyAtMax, entree);
  }
  return entree;
}

// `etat` attendu (angles en degres, azimuts comptes depuis le nord vers l'est):
//   sunAz, sunAlt      position du Soleil
//   moonAz, moonAlt    position de la Lune
//   rSun, rMoon        rayons apparents, en degres
//   dSunKm, dMoonKm    distances, en kilometres (telles quelles dans le JSON)
//   fluxR, fluxG, fluxB flux solaire visible CHEZ L'OBSERVATEUR, 1 = disque entier
//   azimutRegard       azimut vise au centre du panneau
//   altitudeObs        altitude de l'observateur, en metres
//   skyAtMax           champ sky_at_max du site (etoiles + planetes au
//                      maximum d'eclipse, tel quel depuis le JSON) ; absent
//                      ou vide => aucun astre dessine
// `zone` = { x, y, w, h } en pixels de la memoire tampon, origine en bas a
// gauche comme gl.viewport.
//
// Les champs de position, de rayon et de distance sont exactement ceux que
// stateAt() rend: ce module ne les renomme pas et n'en recalcule aucun.
export function createSky(gl) {
  const programme = createProgram(gl, SKY_FS, 'ciel');
  const lieu = (nom) => gl.getUniformLocation(programme, nom);
  const u = {
    zone: lieu('uZone'),
    soleil: lieu('uSoleil'),
    lune: lieu('uLune'),
    flux: lieu('uFlux'),
    rSoleil: lieu('uRSoleil'),
    rLune: lieu('uRLune'),
    dSoleilKm: lieu('uDSoleilKm'),
    dLuneKm: lieu('uDLuneKm'),
    azimutCentre: lieu('uAzimutCentre'),
    altitudeObs: lieu('uAltitudeObs'),
    transmittance: lieu('uTransmittance'),
    multiScatter: lieu('uMultiScatter'),
    fluxLut: lieu('uFluxLut'),
    // Localisation sur l'element [0]: WebGL2 remplit ensuite les elements
    // suivants a partir de la meme localisation, tant que le tableau passe a
    // uniform3fv est fourni au complet -- c'est le comportement standard pour
    // un uniform de type tableau.
    astres: lieu('uAstres[0]'),
    nbAstres: lieu('uNbAstres'),
  };

  // Direction unitaire depuis un azimut et une hauteur en degres, dans le
  // repere du shader: y vers le zenith, x vers l'est, z vers le nord.
  const direction = (azDeg, altDeg) => {
    const az = azDeg * RAD;
    const alt = altDeg * RAD;
    return [Math.cos(alt) * Math.sin(az), Math.sin(alt), Math.cos(alt) * Math.cos(az)];
  };

  return function dessinerCiel(etat, zone, luts) {
    const soleil = direction(etat.sunAz, etat.sunAlt);
    const lune = direction(etat.moonAz, etat.moonAlt);

    // Le ciseau est indispensable des qu'il y aura deux panneaux: le triangle
    // plein cadre de gl.js deborde le viewport, et sans ciseau le second
    // panneau effacerait le premier.
    gl.viewport(zone.x, zone.y, zone.w, zone.h);
    gl.scissor(zone.x, zone.y, zone.w, zone.h);
    gl.enable(gl.SCISSOR_TEST);

    gl.useProgram(programme);
    gl.uniform4f(u.zone, zone.x, zone.y, zone.w, zone.h);
    gl.uniform3f(u.soleil, soleil[0], soleil[1], soleil[2]);
    gl.uniform3f(u.lune, lune[0], lune[1], lune[2]);
    gl.uniform3f(u.flux, etat.fluxR, etat.fluxG, etat.fluxB);
    // Les rayons apparents passent en radians (le shader compare des cordes de
    // vecteurs unitaires); les distances passent en kilometres, telles quelles,
    // et c'est le shader qui les ramene en metres -- une seule conversion, a un
    // seul endroit, la ou elle se lit a cote de la formule de parallaxe.
    gl.uniform1f(u.rSoleil, etat.rSun * RAD);
    gl.uniform1f(u.rLune, etat.rMoon * RAD);
    gl.uniform1f(u.dSoleilKm, etat.dSunKm);
    gl.uniform1f(u.dLuneKm, etat.dMoonKm);
    gl.uniform1f(u.azimutCentre, etat.azimutRegard * RAD);
    gl.uniform1f(u.altitudeObs, etat.altitudeObs);

    // Etoiles et planetes (tache 21) : positions et magnitudes figees a
    // l'instant du maximum d'eclipse, voir le commentaire de sky.glsl.js.
    const { tableau, n } = astresDuSite(etat.skyAtMax);
    gl.uniform1i(u.nbAstres, n);
    if (n > 0) gl.uniform3fv(u.astres, tableau);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, luts.transmittance);
    gl.uniform1i(u.transmittance, 0);

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, luts.flux);
    gl.uniform1i(u.fluxLut, 1);

    gl.activeTexture(gl.TEXTURE2);
    gl.bindTexture(gl.TEXTURE_2D, luts.multiscatter);
    gl.uniform1i(u.multiScatter, 2);
    // L'unite active revient a zero: les liaisons de texture restent en place,
    // seule la cible des prochains bindTexture est remise ou l'appelant
    // l'attend.
    gl.activeTexture(gl.TEXTURE0);

    drawQuad(gl);

    // On rend le contexte comme on l'a trouve: laisser le ciseau arme ferait
    // echouer silencieusement le prochain gl.clear de l'appelant.
    gl.disable(gl.SCISSOR_TEST);
  };
}
