// Rendu d'un panneau de ciel. Ce module ne connait ni la frise, ni le DOM, ni
// les commandes: on lui donne un etat deja calcule, un rectangle de pixels et
// les LUT, il dessine. C'est ce qui permettra a la tache 20 de l'appeler deux
// fois par image, pour deux lieux, sans rien dupliquer.

import { createProgram, drawQuad } from './gl.js';
import { SKY_FS } from './sky.glsl.js';

const RAD = Math.PI / 180;

// `etat` attendu (angles en degres, azimuts comptes depuis le nord vers l'est):
//   sunAz, sunAlt      position du Soleil
//   fluxR, fluxG, fluxB flux solaire visible, 1 = disque entier
//   azimutRegard       azimut vise au centre du panneau
//   altitudeObs        altitude de l'observateur, en metres
// `zone` = { x, y, w, h } en pixels de la memoire tampon, origine en bas a
// gauche comme gl.viewport.
export function createSky(gl) {
  const programme = createProgram(gl, SKY_FS, 'ciel');
  const lieu = (nom) => gl.getUniformLocation(programme, nom);
  const u = {
    zone: lieu('uZone'),
    soleil: lieu('uSoleil'),
    flux: lieu('uFlux'),
    azimutCentre: lieu('uAzimutCentre'),
    altitudeObs: lieu('uAltitudeObs'),
    transmittance: lieu('uTransmittance'),
  };

  return function dessinerCiel(etat, zone, luts) {
    const az = etat.sunAz * RAD;
    const alt = etat.sunAlt * RAD;

    // Le ciseau est indispensable des qu'il y aura deux panneaux: le triangle
    // plein cadre de gl.js deborde le viewport, et sans ciseau le second
    // panneau effacerait le premier.
    gl.viewport(zone.x, zone.y, zone.w, zone.h);
    gl.scissor(zone.x, zone.y, zone.w, zone.h);
    gl.enable(gl.SCISSOR_TEST);

    gl.useProgram(programme);
    gl.uniform4f(u.zone, zone.x, zone.y, zone.w, zone.h);
    gl.uniform3f(
      u.soleil,
      Math.cos(alt) * Math.sin(az), Math.sin(alt), Math.cos(alt) * Math.cos(az),
    );
    gl.uniform3f(u.flux, etat.fluxR, etat.fluxG, etat.fluxB);
    gl.uniform1f(u.azimutCentre, etat.azimutRegard * RAD);
    gl.uniform1f(u.altitudeObs, etat.altitudeObs);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, luts.transmittance);
    gl.uniform1i(u.transmittance, 0);

    drawQuad(gl);

    // On rend le contexte comme on l'a trouve: laisser le ciseau arme ferait
    // echouer silencieusement le prochain gl.clear de l'appelant.
    gl.disable(gl.SCISSOR_TEST);
  };
}
