// Chargement et interpolation de la chronologie de l'eclipse.
// Ce module ignore tout de WebGL et du DOM: il ne fait que des maths sur un
// tableau de nombres, ce qui le rend testable sous node --test.

const CHAMPS = [
  'sunAz', 'sunAlt', 'moonAz', 'moonAlt', 'rSun', 'rMoon',
  'magnitude', 'obscuration', 'fluxR', 'fluxG', 'fluxB', 'dSunKm', 'dMoonKm',
];

// Index des champs qui sont des azimuts: ils s'interpolent par le chemin le
// plus court, sinon un passage par 360 deg produirait un demi-tour complet.
const AZIMUTS = new Set([0, 2]);

// Les contacts et t_max_s arrivent deja en secondes depuis t0_utc: c'est
// build.py qui les a rebases, precisement pour que le navigateur n'ait aucune
// chaine de date a analyser pour se reperer dans les images.
export function parseEclipse(brut) {
  return {
    ...brut,
    sites: brut.sites.map((s) => ({ ...s, t0Ms: Date.parse(s.t0_utc) })),
  };
}

export async function loadEclipse(url) {
  const reponse = await fetch(url);
  if (!reponse.ok) throw new Error(`eclipse: HTTP ${reponse.status}`);
  return parseEclipse(await reponse.json());
}

export function windowSeconds(site) {
  return (site.frames.length - 1) * site.step_s;
}

function melangeAngle(a, b, k) {
  const delta = ((b - a + 540) % 360) - 180;   // ramene dans (-180, 180]
  return (a + delta * k + 360) % 360;
}

export function stateAt(site, secondes) {
  const duree = windowSeconds(site);
  const t = Math.min(Math.max(secondes, 0), duree);
  const position = t / site.step_s;
  const i = Math.min(Math.floor(position), site.frames.length - 2);
  const k = position - i;

  const a = site.frames[i];
  const b = site.frames[i + 1];
  const etat = { t };
  for (let c = 0; c < CHAMPS.length; c++) {
    etat[CHAMPS[c]] = AZIMUTS.has(c)
      ? melangeAngle(a[c], b[c], k)
      : a[c] + (b[c] - a[c]) * k;
  }
  return etat;
}
