// assets/js/contagion/explorer.js
// Le calcul de l'explorateur, sans DOM: correlation, seuil de quantile, delta,
// correction de Forbes-Rigobon. Ce module est importe par la page ET par le
// test node contre les fixtures Python: les memes conventions exactement
// (diviseur n, deux passes, seuil = valeur triee d'indice floor(q*n),
// garde si |x| >= seuil). Toute deviation casse la parite a 1e-12.

export function correlation(xs, ys) {
  const n = xs.length;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
  mx /= n; my /= n;
  let cxy = 0, vx = 0, vy = 0;
  for (let i = 0; i < n; i++) {
    const a = xs[i] - mx, b = ys[i] - my;
    cxy += a * b; vx += a * a; vy += b * b;
  }
  return (cxy / n) / Math.sqrt((vx / n) * (vy / n));
}

export function variance(xs) {
  const n = xs.length;
  let m = 0;
  for (let i = 0; i < n; i++) m += xs[i];
  m /= n;
  let v = 0;
  for (let i = 0; i < n; i++) { const d = xs[i] - m; v += d * d; }
  return v / n;
}

// domaine 0 <= q < 1, comme cote Python: q = 1 sortirait de la table triee.
export function sousEchantillon(rx, ry, q) {
  if (q <= 0) return [rx.slice(), ry.slice()];
  const ampl = rx.map(Math.abs).sort((a, b) => a - b);
  const seuil = ampl[Math.floor(q * ampl.length)];
  const sx = [], sy = [];
  for (let i = 0; i < rx.length; i++) {
    if (Math.abs(rx[i]) >= seuil) { sx.push(rx[i]); sy.push(ry[i]); }
  }
  return [sx, sy];
}

export function deltaRelatif(sousX, pleinX) {
  return variance(sousX) / variance(pleinX) - 1;
}

export function correctionFR(rhoCond, delta) {
  return rhoCond / Math.sqrt(1 + delta * (1 - rhoCond * rhoCond));
}

export function analyse(rx, ry, q) {
  const [sx, sy] = sousEchantillon(rx, ry, q);
  const delta = deltaRelatif(sx, rx);
  const rho = correlation(sx, sy);
  return { n: sx.length, delta, rho, rho_corrigee: correctionFR(rho, delta) };
}
