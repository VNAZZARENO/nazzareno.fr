// Rendu d'un panneau de ciel. Ce module ne connait ni la frise, ni le DOM, ni
// les commandes: on lui donne un etat deja calcule, un rectangle de pixels et
// les LUT, il dessine. C'est ce qui permettra a la tache 20 de l'appeler deux
// fois par image, pour deux lieux, sans rien dupliquer.

import { createProgram, drawQuad } from './gl.js';
import { SKY_FS } from './sky.glsl.js';

const RAD = Math.PI / 180;

// `etat` attendu (angles en degres, azimuts comptes depuis le nord vers l'est):
//   sunAz, sunAlt      position du Soleil
//   moonAz, moonAlt    position de la Lune
//   rSun, rMoon        rayons apparents, en degres
//   dSunKm, dMoonKm    distances, en kilometres (telles quelles dans le JSON)
//   fluxR, fluxG, fluxB flux solaire visible CHEZ L'OBSERVATEUR, 1 = disque entier
//   azimutRegard       azimut vise au centre du panneau
//   altitudeObs        altitude de l'observateur, en metres
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
    fluxLut: lieu('uFluxLut'),
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

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, luts.transmittance);
    gl.uniform1i(u.transmittance, 0);

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, luts.flux);
    gl.uniform1i(u.fluxLut, 1);
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
