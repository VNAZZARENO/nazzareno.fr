// Point d'entree du simulateur. Regle qui gouverne tout ce fichier : on ne
// dessine que si quelque chose a change. Frise a l'arret et regard immobile
// => zero appel de dessin => zero CPU. Chaque source d'evenement (redimensio-
// nnement, visibilite, defilement, lecture) ne fait qu'une chose : lever le
// drapeau `sale`. La boucle rAF est la seule a l'abaisser, et seulement apres
// avoir dessine.
//
// A ce stade, dessiner() rend UN panneau plein cadre, sans Lune : un ciel
// ordinaire, pour verifier le modele de diffusion avant d'y ajouter l'eclipse
// (tache 18). Les deux panneaux et les commandes arrivent a la tache 20.

import { createContext } from './gl.js';
import { loadEclipse, stateAt } from './data.js';
import { buildLuts } from './luts.js';
import { createSky } from './sky.js';

const URL_DONNEES = '/assets/data/eclipse-2026-08-12.json';
const SITE_GAUCHE = 'paris';
const SITE_DROIT = 'espagne';

export async function init(racine) {
  const canvas = racine.querySelector('canvas.sim-canvas');
  if (!canvas) return;

  const gl = createContext(canvas);
  if (!gl) return; // pas de WebGL2 utilisable : on reste sur le HTML statique

  const eclipse = await loadEclipse(URL_DONNEES);

  // Les LUT ne dependent ni du lieu ni de l'instant : une seule construction,
  // partagee par tous les panneaux, faite avant la premiere image.
  const luts = buildLuts(gl);
  const dessinerCiel = createSky(gl);
  const siteGauche = eclipse.sites.find((s) => s.id === SITE_GAUCHE);

  // Etat du simulateur. Rien ne le pilote encore (taches 20+) : on ne fait
  // que le porter, pour que les prochaines taches n'aient qu'a le lire/ecrire
  // sans retoucher ce fichier.
  const etat = {
    siteGauche: SITE_GAUCHE,
    siteDroit: SITE_DROIT,
    tSecondes: 0,
    azimutRegard: 0,
    enLecture: false,
    visible: false,
    sale: true, // premier rendu obligatoire
  };

  const reduireMouvement = window.matchMedia('(prefers-reduced-motion: reduce)');
  // enLecture reste false tant que l'utilisateur n'a rien demande : pas de
  // lecture automatique, avec ou sans prefers-reduced-motion. On ecoute quand
  // meme le changement pour que la tache 20 puisse s'y fier sans reecrire
  // cette logique.
  const surChangementMouvement = () => { etat.sale = true; };
  reduireMouvement.addEventListener('change', surChangementMouvement);

  // Hors ecran => on arrete de dessiner, meme si sale reste pose. Quand le
  // canevas revient, on force un redessin (l'etat a pu changer pendant qu'on
  // ne regardait rien, ou pas : ca ne coute qu'une image).
  const observateur = new IntersectionObserver((entrees) => {
    for (const entree of entrees) {
      etat.visible = entree.isIntersecting;
      if (etat.visible) etat.sale = true;
    }
  });
  observateur.observe(canvas);

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) etat.sale = true;
  });

  // La memoire tampon de dessin est dimensionnee sous la resolution CSS :
  // min(devicePixelRatio, 1.5) * 0.7. Un ciel simule n'a pas besoin de la
  // nettete d'un ecran Retina plein pot, et ce facteur economise beaucoup de
  // pixels a remplir pour un rendu qui restera flou par nature (diffusion).
  function tailleCible() {
    const rect = canvas.getBoundingClientRect();
    const echelle = Math.min(window.devicePixelRatio || 1, 1.5) * 0.7;
    return {
      largeur: Math.max(1, Math.round(rect.width * echelle)),
      hauteur: Math.max(1, Math.round(rect.height * echelle)),
    };
  }

  function redimensionner() {
    const { largeur, hauteur } = tailleCible();
    if (canvas.width === largeur && canvas.height === hauteur) return;
    canvas.width = largeur;
    canvas.height = hauteur;
    etat.sale = true;
  }

  // Le canevas est display:none tant que data-webgl n'est pas pose (voir
  // style.css) : getBoundingClientRect() y renverrait 0x0 et figerait la
  // memoire tampon a 1x1 pixel. On revele donc le canevas avant de le
  // dimensionner, jamais apres.
  racine.dataset.webgl = 'ok';
  window.addEventListener('resize', redimensionner);
  redimensionner();

  // Tache 17 : un seul panneau, plein cadre, et pas d'eclipse. Le flux visible
  // est force a 1 -- c'est-a-dire le Soleil entier -- pour que ce point de
  // controle ne juge que le modele de diffusion. La Lune arrive a la tache 18,
  // le second panneau a la tache 20.
  function dessiner() {
    const instant = stateAt(siteGauche, etat.tSecondes);
    dessinerCiel({
      sunAz: instant.sunAz,
      sunAlt: instant.sunAlt,
      fluxR: 1, fluxG: 1, fluxB: 1,
      azimutRegard: instant.sunAz + etat.azimutRegard,
      altitudeObs: siteGauche.elevation_m,
    }, { x: 0, y: 0, w: canvas.width, h: canvas.height }, luts);
    // Compteur de verification du drapeau dirty, actif seulement derriere
    // un flag explicite : jamais de cout ni de bruit en production.
    if (window.__ECLIPSE_DEBUG__) {
      window.__eclipseDessins = (window.__eclipseDessins || 0) + 1;
    }
  }

  function boucle() {
    if (etat.sale && etat.visible && !document.hidden) {
      dessiner();
      etat.sale = false;
    }
    requestAnimationFrame(boucle);
  }

  requestAnimationFrame(boucle);

  // Expose pour la tache 20 et pour le debogage : rien ici ne doit devenir
  // une dependance cachee de ce module envers l'exterieur.
  return { gl, etat, canvas, eclipse };
}
