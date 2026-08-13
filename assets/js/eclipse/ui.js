// Commandes du simulateur : deux selecteurs de lieu, lecture/pause, frise, et
// une lecture chiffree par panneau. Ce module ne connait que data.js et le DOM
// — pas une ligne de WebGL. Il ne dessine jamais : il modifie `etat` et appelle
// `onChange`, a charge de l'appelant de lever son drapeau `sale`.
//
// Le point delicat de cette tache est la frise. Les trois lieux n'ont ni le
// meme t0_utc (Paris 17:17:15, Palma 17:33:05, Reykjavik 16:42:14) ni la meme
// duree de fenetre. Mettre les deux panneaux sur les secondes locales de
// chacun afficherait deux instants differents cote a cote : la comparaison
// serait un mensonge. La frise porte donc un instant ABSOLU en millisecondes
// (`etat.instantMs`), et chaque panneau en deduit ses propres secondes locales
// par (instantMs - site.t0Ms) / 1000.

import { stateAt, windowSeconds } from './data.js';

const PAS_FRISE = 1000;          // resolution du curseur, 0..1000
const DUREE_LECTURE_MS = 40000;  // toute la frise parcourue en 40 s
const PAS_CLAVIER_DEG = 4;       // rotation du regard par appui sur une fleche
const DEG_PAR_LARGEUR = 120;     // rotation pour un glisse sur toute la largeur
const PERIODE_SORTIE_MS = 1000;  // au plus une annonce par seconde et par panneau

// Secondes locales d'un site pour un instant absolu. Peut sortir de [0, duree]:
// stateAt borne de lui-meme, et `dansLaFenetre` permet de le dire a l'utilisateur
// plutot que de faire passer une image gelee pour un calcul.
export function secondesLocales(site, instantMs) {
  return (instantMs - site.t0Ms) / 1000;
}

export function dansLaFenetre(site, instantMs) {
  const t = secondesLocales(site, instantMs);
  return t >= 0 && t <= windowSeconds(site);
}

// Bornes absolues couvertes par une paire de sites : l'union de leurs fenetres.
// Union et non intersection, pour qu'aucun contact d'aucun des deux panneaux ne
// soit hors de portee du curseur.
export function bornesAbsolues(sites) {
  let debut = Infinity;
  let fin = -Infinity;
  for (const site of sites) {
    debut = Math.min(debut, site.t0Ms);
    fin = Math.max(fin, site.t0Ms + windowSeconds(site) * 1000);
  }
  return { debut, fin };
}

const borner = (v, min, max) => Math.min(Math.max(v, min), max);

// Ramene un angle dans (-180, 180] : le regard tourne indefiniment, mais la
// valeur stockee ne doit pas deriver vers des milliers de degres.
const normaliserAngle = (a) => ((a + 180) % 360 + 360) % 360 - 180;

export function createUi({ racine, canvas, eclipse, etat, onChange }) {
  const commandes = racine.querySelector('.sim-controls');
  if (!commandes) return null;

  const champ = (sel) => commandes.querySelector(sel);
  const selecteurs = {
    gauche: champ('select[data-panneau="gauche"]'),
    droit: champ('select[data-panneau="droit"]'),
  };
  const bouton = champ('button[data-role="lecture"]');
  const frise = champ('input[data-role="frise"]');
  const sorties = {
    gauche: champ('output[data-panneau="gauche"]'),
    droit: champ('output[data-panneau="droit"]'),
  };
  // Si le balisage n'est pas complet on ne cable rien : mieux vaut aucune
  // commande qu'une moitie de commande.
  if (!selecteurs.gauche || !selecteurs.droit || !bouton || !frise
      || !sorties.gauche || !sorties.droit) return null;

  // Toutes les chaines traduisibles viennent du HTML, jamais d'un dictionnaire
  // cache dans le JS : la page anglaise et la page francaise portent chacune
  // les siennes.
  const textes = commandes.dataset;
  const langue = document.documentElement.lang || 'fr';
  const enAnglais = langue.startsWith('en');
  const nomSite = (site) => (enAnglais ? site.name_en : site.name_fr);

  const siteDe = (id) => eclipse.sites.find((s) => s.id === id) ?? eclipse.sites[0];
  const paire = () => [siteDe(etat.siteGauche), siteDe(etat.siteDroit)];

  // ---- formats de nombres et d'heures -------------------------------------
  const nbAltitude = new Intl.NumberFormat(langue, {
    minimumFractionDigits: 1, maximumFractionDigits: 1,
  });
  const nbMagnitude = new Intl.NumberFormat(langue, {
    minimumFractionDigits: 3, maximumFractionDigits: 3,
  });
  const nbObscuration = new Intl.NumberFormat(langue, {
    style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1,
  });
  // Un formateur d'heure par fuseau, construit une fois : Intl.DateTimeFormat
  // est cher, et il en faudrait un par image sinon.
  const horloges = new Map();
  function horloge(site) {
    let h = horloges.get(site.tz);
    if (!h) {
      h = new Intl.DateTimeFormat(langue, {
        timeZone: site.tz,
        hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
      });
      horloges.set(site.tz, h);
    }
    return h;
  }

  // ---- les selecteurs de lieu ---------------------------------------------
  // Les options sont construites depuis le JSON et non ecrites dans le HTML :
  // une seule source pour la liste des lieux et pour leurs noms.
  for (const cote of ['gauche', 'droit']) {
    const select = selecteurs[cote];
    select.replaceChildren();
    for (const site of eclipse.sites) {
      const option = document.createElement('option');
      option.value = site.id;
      option.textContent = nomSite(site);
      select.append(option);
    }
    select.value = cote === 'gauche' ? etat.siteGauche : etat.siteDroit;
  }

  // ---- la frise ------------------------------------------------------------
  frise.min = '0';
  frise.max = String(PAS_FRISE);
  frise.step = '1';

  function poserFrise() {
    const { debut, fin } = bornesAbsolues(paire());
    etat.instantMs = borner(etat.instantMs, debut, fin);
    const k = fin > debut ? (etat.instantMs - debut) / (fin - debut) : 0;
    frise.value = String(Math.round(k * PAS_FRISE));
  }

  function lireFrise() {
    const { debut, fin } = bornesAbsolues(paire());
    etat.instantMs = debut + (Number(frise.value) / PAS_FRISE) * (fin - debut);
  }

  // ---- les lectures chiffrees ---------------------------------------------
  function texteSortie(site) {
    const instant = stateAt(site, secondesLocales(site, etat.instantMs));
    const morceaux = [
      nomSite(site),
      horloge(site).format(new Date(etat.instantMs)),
      `${textes.motSoleil} ${nbAltitude.format(instant.sunAlt)}°`,
      `${textes.motMagnitude} ${nbMagnitude.format(instant.magnitude)}`,
      `${textes.motObscuration} ${nbObscuration.format(instant.obscuration)}`,
    ];
    // Hors fenetre calculee, stateAt rend l'image de bord : on le dit, plutot
    // que de laisser croire que le ciel gele est un resultat.
    if (!dansLaFenetre(site, etat.instantMs)) morceaux.push(textes.motHors);
    return morceaux.join(' · ');
  }

  let dernierEcrit = -Infinity;
  let minuteurSortie = 0;

  function ecrireSorties() {
    dernierEcrit = performance.now();
    const sites = paire();
    for (const [i, cote] of ['gauche', 'droit'].entries()) {
      const texte = texteSortie(sites[i]);
      // aria-live reannonce a chaque ecriture, meme identique : on ne touche
      // au noeud que si la valeur a reellement change.
      if (sorties[cote].textContent !== texte) sorties[cote].textContent = texte;
    }
  }

  // Au plus une ecriture par seconde, front montant puis front descendant : le
  // lecteur d'ecran n'est pas noye pendant un glisse ou une lecture, et la
  // derniere valeur finit toujours par etre annoncee.
  function demanderSorties() {
    const reste = PERIODE_SORTIE_MS - (performance.now() - dernierEcrit);
    if (reste <= 0) {
      if (minuteurSortie) { clearTimeout(minuteurSortie); minuteurSortie = 0; }
      ecrireSorties();
      return;
    }
    if (!minuteurSortie) {
      minuteurSortie = setTimeout(() => { minuteurSortie = 0; ecrireSorties(); }, reste);
    }
  }

  // Le seul point par lequel ce module reveille le rendu.
  const redessiner = () => { onChange(); };
  const redessinerEtAnnoncer = () => { onChange(); demanderSorties(); };

  // ---- lecture / pause -----------------------------------------------------
  const reduireMouvement = window.matchMedia('(prefers-reduced-motion: reduce)');
  let idAnimation = 0;
  let horodatagePrecedent = 0;

  function etiqueterBouton() {
    bouton.setAttribute('aria-pressed', etat.enLecture ? 'true' : 'false');
    bouton.textContent = etat.enLecture ? textes.motPause : textes.motLecture;
  }

  function arreter() {
    if (idAnimation) cancelAnimationFrame(idAnimation);
    idAnimation = 0;
    etat.enLecture = false;
    etiqueterBouton();
  }

  function avancer(horodatage) {
    if (!etat.enLecture) return;
    const { debut, fin } = bornesAbsolues(paire());
    const dt = horodatagePrecedent ? horodatage - horodatagePrecedent : 0;
    horodatagePrecedent = horodatage;
    etat.instantMs += dt * ((fin - debut) / DUREE_LECTURE_MS);
    if (etat.instantMs >= fin) {
      etat.instantMs = fin;
      poserFrise();
      redessinerEtAnnoncer();
      arreter();
      return;
    }
    poserFrise();
    redessinerEtAnnoncer();
    idAnimation = requestAnimationFrame(avancer);
  }

  function demarrer() {
    const { debut, fin } = bornesAbsolues(paire());
    if (etat.instantMs >= fin) etat.instantMs = debut; // rejouer depuis le debut
    etat.enLecture = true;
    horodatagePrecedent = 0;
    etiqueterBouton();
    idAnimation = requestAnimationFrame(avancer);
  }

  bouton.addEventListener('click', () => {
    if (etat.enLecture) arreter(); else demarrer();
  });

  // prefers-reduced-motion n'interdit pas la commande — la frise et le bouton
  // restent utilisables — mais rien ne demarre tout seul, et si la preference
  // apparait en cours de lecture on s'arrete.
  reduireMouvement.addEventListener('change', () => {
    if (reduireMouvement.matches) arreter();
  });

  // ---- cablage des commandes ----------------------------------------------
  frise.addEventListener('input', () => {
    arreter();
    lireFrise();
    redessinerEtAnnoncer();
  });

  for (const cote of ['gauche', 'droit']) {
    selecteurs[cote].addEventListener('change', (evenement) => {
      if (cote === 'gauche') etat.siteGauche = evenement.target.value;
      else etat.siteDroit = evenement.target.value;
      // L'instant absolu est conserve, seules les bornes changent : le curseur
      // saute parce que l'axe a change, pas parce que l'heure a change.
      poserFrise();
      redessinerEtAnnoncer();
    });
  }

  // ---- le regard, partage par les deux panneaux ---------------------------
  // `etat.azimutRegard` est un ECART applique a l'azimut solaire de chaque
  // lieu : les deux vues restent cadrees de la meme facon par rapport a leur
  // propre Soleil, donc comparables.
  function tournerRegard(deltaDeg) {
    etat.azimutRegard = normaliserAngle(etat.azimutRegard + deltaDeg);
    redessiner(); // les lectures chiffrees ne dependent pas du regard
  }

  let pointeurActif = null;
  let xPrecedent = 0;

  canvas.addEventListener('pointerdown', (evenement) => {
    if (pointeurActif !== null) return;
    pointeurActif = evenement.pointerId;
    xPrecedent = evenement.clientX;
    canvas.setPointerCapture(pointeurActif);
  });

  canvas.addEventListener('pointermove', (evenement) => {
    if (evenement.pointerId !== pointeurActif) return;
    const largeur = canvas.getBoundingClientRect().width || 1;
    const dx = evenement.clientX - xPrecedent;
    xPrecedent = evenement.clientX;
    // Tirer le ciel vers la droite fait tourner le regard vers la gauche.
    tournerRegard(-dx / largeur * DEG_PAR_LARGEUR);
  });

  const relacher = (evenement) => {
    if (evenement.pointerId !== pointeurActif) return;
    if (canvas.hasPointerCapture(pointeurActif)) canvas.releasePointerCapture(pointeurActif);
    pointeurActif = null;
  };
  canvas.addEventListener('pointerup', relacher);
  canvas.addEventListener('pointercancel', relacher);

  canvas.addEventListener('keydown', (evenement) => {
    if (evenement.altKey || evenement.ctrlKey || evenement.metaKey) return;
    if (evenement.key === 'ArrowLeft') tournerRegard(-PAS_CLAVIER_DEG);
    else if (evenement.key === 'ArrowRight') tournerRegard(PAS_CLAVIER_DEG);
    else return;
    evenement.preventDefault(); // sinon la page defile sous le curseur
  });

  // ---- etat initial --------------------------------------------------------
  etiqueterBouton();
  poserFrise();
  ecrireSorties();

  return { poserFrise, ecrireSorties, arreter };
}
