// Point d'entree du simulateur. Regle qui gouverne tout ce fichier : on ne
// dessine que si quelque chose a change. Frise a l'arret et regard immobile
// => zero appel de dessin => zero CPU. Chaque source d'evenement (redimensio-
// nnement, visibilite, defilement, lecture) ne fait qu'une chose : lever le
// drapeau `sale`. La boucle rAF est la seule a l'abaisser, et seulement apres
// avoir dessine.
//
// A ce stade, dessiner() rend DEUX panneaux, un par lieu, au meme instant
// absolu : c'est la demonstration de la page. Le decoupage du cadre est ici,
// le cablage des commandes est dans ui.js, le rendu d'un ciel dans sky.js.

import { createContext } from './gl.js';
import { loadEclipse, stateAt } from './data.js';
import { buildLuts } from './luts.js';
import { createSky } from './sky.js';
import { createInset } from './inset.js';
import { createUi, secondesLocales } from './ui.js';

const URL_DONNEES = '/assets/data/eclipse-2026-08-12.json';
const SITE_GAUCHE = 'paris';
const SITE_DROIT = 'espagne';

// Ecart d'azimut applique au regard, relativement au Soleil de CHAQUE lieu.
// Zero (regarder le Soleil en face) rendrait Palma presque noir a la totalite :
// le Soleil y est a 2,64° de hauteur, l'axe de l'ombre est donc quasi
// horizontal, et l'anneau crepusculaire se trouve sur les cotes, pas devant.
// A 35° le Soleil reste franchement dans le champ (108° de large par panneau en
// paysage, donc au cinquieme gauche du cadre) et les deux tiers droits montrent
// le ciel encore eclaire hors de l'ombre : a Palma on voit le cone sombre a
// gauche et le crepuscule s'allumer a droite, a Paris le meme cadrage montre
// une fin de journee ordinaire. C'est cette comparaison-la que la page doit
// rendre, pas un rectangle noir.
const ECART_REGARD_DEG = 35;

// Paire et instant imposes a la route ?poster=1, independamment des defauts
// ci-dessus : l'image de repli doit toujours montrer la meme chose, Paris
// encore en plein jour a gauche et Palma dans la totalite a droite.
const POSTER_GAUCHE = 'paris';
const POSTER_DROIT = 'espagne';

export async function init(racine) {
  const canvas = racine.querySelector('canvas.sim-canvas');
  if (!canvas) return;

  // Deux routes de service, toutes deux commandees par la barre d'adresse et
  // sans le moindre effet — ni cout — sur la page ordinaire.
  //   ?poster=1 fabrique l'image de repli AVEC le simulateur lui-meme, plutot
  //             que de dessiner a cote une illustration qui divergerait au
  //             premier changement de shader.
  //   ?debug=1  affiche le compteur d'images et l'etat courant, de quoi
  //             verifier de visu que la page ne dessine rien au repos.
  const parametres = new URLSearchParams(location.search);
  const modePoster = parametres.get('poster') === '1';
  const modeDebug = parametres.get('debug') === '1';

  const gl = createContext(canvas, { preserveDrawingBuffer: modePoster });
  if (!gl) return; // pas de WebGL2 utilisable : on reste sur le HTML statique

  // La LUT de flux est en RGB32F et le shader du ciel l'echantillonne en
  // filtrage lineaire (256 texels seulement pour toute la separation, et le
  // bord de l'ombre n'en couvre que quelques-uns : le plus proche voisin y
  // ferait des marches bien visibles). Sans cette extension, une texture
  // flottante filtree en lineaire est INCOMPLETE et toute lecture rend du
  // noir : le ciel disparaitrait entierement, sans la moindre erreur WebGL.
  // On prefere donc renoncer, exactement comme pour WebGL2 lui-meme.
  if (!gl.getExtension('OES_texture_float_linear')) return;

  const eclipse = await loadEclipse(URL_DONNEES);

  // Les LUT ne dependent ni du lieu ni de l'instant : une seule construction,
  // partagee par tous les panneaux, faite avant la premiere image.
  const luts = buildLuts(gl);
  const dessinerCiel = createSky(gl);
  const dessinerEncart = createInset(gl);

  // Les sites sont resolus a chaque image depuis `etat`, et non captures une
  // fois pour toutes : les selecteurs de ui.js ecrivent `etat.siteGauche` et
  // `etat.siteDroit`, et il ne doit y avoir aucun etat de site fige ailleurs.
  const siteDe = (id) => eclipse.sites.find((s) => s.id === id) ?? eclipse.sites[0];

  // Etat du simulateur. `instantMs` est un instant ABSOLU (epoch UTC) et non
  // des secondes locales : c'est la seule facon de mettre deux lieux dont les
  // t0_utc different de plusieurs dizaines de minutes sur la meme frise. La
  // valeur d'ouverture est le maximum d'eclipse du panneau de droite, soit
  // Palma a 18:31:45 UTC : la page s'ouvre sur ce qu'elle a a montrer.
  const idGauche = modePoster ? POSTER_GAUCHE : SITE_GAUCHE;
  const idDroit = modePoster ? POSTER_DROIT : SITE_DROIT;
  const droitInitial = siteDe(idDroit);
  const etat = {
    siteGauche: idGauche,
    siteDroit: idDroit,
    instantMs: droitInitial.t0Ms + droitInitial.t_max_s * 1000,
    azimutRegard: ECART_REGARD_DEG,
    enLecture: false,
    visible: false,
    sale: true, // premier rendu obligatoire
  };

  const reduireMouvement = window.matchMedia('(prefers-reduced-motion: reduce)');
  // enLecture reste false tant que l'utilisateur n'a rien demande : pas de
  // lecture automatique, avec ou sans prefers-reduced-motion. ui.js arrete en
  // plus une lecture en cours si la preference apparait.
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
  // Le plafond a 1,5 et le facteur 0,7 sont deux mesures de cadence d'images :
  // ils n'ont plus de sens pour une image fixe encodee une seule fois. La route
  // poster rend donc a l'echelle 1,0 et au ratio de pixels reel du navigateur
  // de capture, ce qui donne un fichier utilisable comme repli et comme source
  // des vignettes de partage.
  function tailleCible() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const echelle = modePoster ? dpr : Math.min(dpr, 1.5) * 0.7;
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
  // Les commandes sont cablees avant de reveler le simulateur : les selecteurs
  // sont remplis depuis le JSON, donc jamais vides a l'ecran.
  createUi({ racine, canvas, eclipse, etat, onChange: () => { etat.sale = true; } });

  racine.dataset.webgl = 'ok';
  window.addEventListener('resize', redimensionner);
  redimensionner();

  // Decoupage du cadre en deux panneaux. En paysage ils sont cote a cote, et
  // sous 48rem la feuille de style bascule le cadre en 4/5 : le cadre devient
  // plus haut que large et les panneaux s'empilent. On lit donc la forme de la
  // memoire tampon plutot que de dupliquer le point de rupture en JS.
  // L'origine des zones est en bas a gauche (comme gl.viewport), d'ou le
  // panneau « gauche » place EN HAUT quand on empile.
  // Le partage est exact (floor + reste) : les deux zones couvrent tous les
  // pixels, sans gouttiere, donc aucun gl.clear n'est necessaire.
  function zones() {
    const l = canvas.width;
    const h = canvas.height;
    if (l >= h) {
      const coupe = Math.floor(l / 2);
      return [{ x: 0, y: 0, w: coupe, h }, { x: coupe, y: 0, w: l - coupe, h }];
    }
    const coupe = Math.floor(h / 2);
    return [{ x: 0, y: coupe, w: l, h: h - coupe }, { x: 0, y: 0, w: l, h: coupe }];
  }

  // Encart teleobjectif d'un panneau (tache 22) : un carre en BAS A DROITE du
  // panneau, cote a 30 % de sa plus petite dimension, avec une marge. La regle
  // est exprimee relativement au panneau et non au cadre entier, donc elle
  // s'applique telle quelle a la disposition empilee : chaque panneau porte le
  // sien, a la meme place et a la meme taille relative.
  // L'origine etant en bas a gauche, « bas a droite » est bien x maximal et y
  // minimal.
  const PART_ENCART = 0.30;
  const PART_MARGE = 0.04;

  function encart(zone) {
    const petit = Math.min(zone.w, zone.h);
    const cote = Math.max(1, Math.round(PART_ENCART * petit));
    const marge = Math.round(PART_MARGE * petit);
    return {
      x: zone.x + zone.w - cote - marge,
      y: zone.y + marge,
      w: cote,
      h: cote,
    };
  }

  // ---- instrumentation ?debug=1 -------------------------------------------
  // Le compteur d'appels de dessin passe par gl.drawArrays lui-meme plutot que
  // par un nombre ecrit a la main dans dessiner() : il compte ce que le pilote
  // a reellement recu, encart et LUTs compris. Le remplacement de la methode
  // n'existe que sous ?debug=1, jamais en production.
  let appelsDessin = 0;
  if (modeDebug) {
    const dessinOriginal = gl.drawArrays.bind(gl);
    gl.drawArrays = (mode, premier, nombre) => {
      appelsDessin++;
      dessinOriginal(mode, premier, nombre);
    };
  }

  // Deux panneaux, deux lieux, UN instant absolu. Chaque site convertit cet
  // instant en ses propres secondes locales via son t0_utc ; c'est la seule
  // chose qui rend la comparaison honnete. Tout le reste sort tel quel des
  // ephemerides : positions, rayons, distances et flux.
  function dessiner() {
    appelsDessin = 0;
    const sites = [siteDe(etat.siteGauche), siteDe(etat.siteDroit)];
    const cadres = zones();
    for (let i = 0; i < 2; i++) {
      const site = sites[i];
      const instant = stateAt(site, secondesLocales(site, etat.instantMs));
      dessinerCiel({
        sunAz: instant.sunAz,
        sunAlt: instant.sunAlt,
        moonAz: instant.moonAz,
        moonAlt: instant.moonAlt,
        rSun: instant.rSun,
        rMoon: instant.rMoon,
        dSunKm: instant.dSunKm,
        dMoonKm: instant.dMoonKm,
        fluxR: instant.fluxR, fluxG: instant.fluxG, fluxB: instant.fluxB,
        // L'ecart de regard est partage : applique a l'azimut solaire propre a
        // chaque lieu, il cadre les deux ciels de la meme facon.
        azimutRegard: instant.sunAz + etat.azimutRegard,
        altitudeObs: site.elevation_m,
        // Etoiles et planetes (tache 21) : figees a l'instant du maximum
        // d'eclipse (sky_at_max), pas recalculees par image -- voir le
        // commentaire de sky.glsl.js pour pourquoi c'est sans consequence
        // visible sur la duree de la totalite.
        skyAtMax: site.sky_at_max,
      }, cadres[i], luts);

      // L'encart passe APRES le ciel du meme panneau : il se dessine dessus.
      // Il recoit le meme `instant`, donc exactement les memes ephemerides que
      // le ciel et que la lecture chiffree — il n'y a pas de seconde source de
      // verite pour la geometrie des deux disques.
      dessinerEncart({
        sunAz: instant.sunAz,
        sunAlt: instant.sunAlt,
        moonAz: instant.moonAz,
        moonAlt: instant.moonAlt,
        rSun: instant.rSun,
        rMoon: instant.rMoon,
        fluxR: instant.fluxR, fluxG: instant.fluxG, fluxB: instant.fluxB,
      }, encart(cadres[i]));
    }
    // Compteur de verification du drapeau dirty, actif seulement derriere
    // un flag explicite : jamais de cout ni de bruit en production.
    if (modeDebug || window.__ECLIPSE_DEBUG__) {
      window.__eclipseDessins = (window.__eclipseDessins || 0) + 1;
    }
  }

  // ---- superposition de debogage ------------------------------------------
  // Images par seconde, appels de dessin de la derniere image, taille de la
  // memoire tampon, et les valeurs courantes des deux panneaux. C'est de quoi
  // constater de visu l'engagement principal du projet : au repos, le compteur
  // d'images par seconde tombe a zero et le total cesse de monter.
  function creerDebug() {
    const boite = document.createElement('div');
    boite.className = 'sim-debug';
    boite.setAttribute('aria-hidden', 'true'); // doublon des <output>, pas une information de plus
    racine.append(boite);

    let total = 0;
    let derniersAppels = 0;
    const horodatages = []; // instants des dessins de la derniere seconde

    const ligne = (id) => {
      const site = siteDe(id);
      const t = secondesLocales(site, etat.instantMs);
      const e = stateAt(site, t);
      return `${site.id.padEnd(9)} t=${t.toFixed(0).padStart(4)}s`
        + ` h=${e.sunAlt.toFixed(2)}° az=${e.sunAz.toFixed(2)}°`
        + ` mag=${e.magnitude.toFixed(3)} obs=${(e.obscuration * 100).toFixed(2)}%`
        + ` flux=${e.fluxR.toExponential(2)}/${e.fluxG.toExponential(2)}/${e.fluxB.toExponential(2)}`;
    };

    function ecrire() {
      const maintenant = performance.now();
      while (horodatages.length && maintenant - horodatages[0] > 1000) horodatages.shift();
      boite.textContent = [
        `${horodatages.length} img/s · ${total} image(s) dessinee(s) au total`,
        `${derniersAppels} appel(s) de dessin a la derniere image`,
        `tampon ${canvas.width}×${canvas.height} · dpr ${(window.devicePixelRatio || 1).toFixed(2)}`,
        `regard ${etat.azimutRegard >= 0 ? '+' : ''}${etat.azimutRegard.toFixed(1)}° · ${etat.enLecture ? 'lecture' : 'arret'}`,
        ligne(etat.siteGauche),
        ligne(etat.siteDroit),
      ].join('\n');
    }

    // La fenetre glissante doit retomber a zero quand plus rien n'est dessine,
    // donc il faut un reveil periodique independant du rendu. Ce minuteur est
    // le seul travail recurrent de toute la page, et il n'existe que sous
    // ?debug=1 : la mesure du repos ne doit pas etre faite par ce qui l'empeche.
    setInterval(ecrire, 250);
    ecrire();

    return (appels) => {
      total++;
      derniersAppels = appels;
      horodatages.push(performance.now());
      ecrire();
    };
  }

  const noterDessin = modeDebug ? creerDebug() : null;

  // ---- route ?poster=1 -----------------------------------------------------
  // Une seule image, encodee en PNG et telechargee. C'est cette image-la qui
  // devient assets/img/eclipse-poster.webp : le repli sans WebGL est donc
  // produit par le simulateur, et ne peut pas diverger de lui.
  let posterExporte = false;

  function exporterPoster() {
    posterExporte = true;
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const lien = document.createElement('a');
      lien.href = url;
      lien.download = 'eclipse-poster.png';
      document.body.append(lien);
      lien.click();
      lien.remove();
      // Un revoke immediat couperait le telechargement en cours dans certains
      // navigateurs ; l'URL vit le temps de l'ecriture du fichier.
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      racine.dataset.poster = 'pret'; // repere pour une capture automatisee
    }, 'image/png');
  }

  function boucle() {
    // En mode poster on ne consulte ni l'observateur d'intersection ni la
    // visibilite de l'onglet : l'image doit sortir meme si le canevas est hors
    // ecran ou l'onglet en arriere-plan pendant la capture.
    if (etat.sale && (modePoster || (etat.visible && !document.hidden))) {
      dessiner();
      etat.sale = false;
      if (noterDessin) noterDessin(appelsDessin);
      if (modePoster && !posterExporte) exporterPoster();
    }
    requestAnimationFrame(boucle);
  }

  requestAnimationFrame(boucle);

  // Expose pour la tache 20 et pour le debogage : rien ici ne doit devenir
  // une dependance cachee de ce module envers l'exterieur.
  return { gl, etat, canvas, eclipse };
}
