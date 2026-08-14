"""Correlation par decile d'amplitude du rendement source, brute et corrigee.

Le conditionnement est |x| CONTEMPORAIN, pas une volatilite glissante: c'est
la version pure du biais de selection, celle qui opere meme dans un monde
i.i.d. sans memoire, et donc celle que la figure du retournement exige. Chaque
point porte son intervalle a 95 % par bootstrap i.i.d. au sein du decile
(B = 2000, graine fixee); ce bootstrap ignore la dependance serielle et
sous-estime donc un peu la largeur, ce que la page dit en clair.
"""
import numpy as np

from tools.contagion.bias import correction, delta_relatif
from tools.contagion.simulate import correlation

B_BOOTSTRAP = 2000


def par_deciles(x, y, n_tranches=10, graine_bootstrap=20260814):
    x, y = np.asarray(x, float), np.asarray(y, float)
    var_pleine = x.var()
    ordre = np.argsort(np.abs(x), kind="stable")
    bornes = [round(i * len(x) / n_tranches) for i in range(n_tranches + 1)]
    rng = np.random.default_rng(graine_bootstrap)
    tranches = []
    for i in range(n_tranches):
        idx = ordre[bornes[i]:bornes[i + 1]]
        xb, yb = x[idx], y[idx]
        delta = delta_relatif(xb.var(), var_pleine)
        rho = correlation(xb, yb)
        tirage_rho, tirage_corr = [], []
        for _ in range(B_BOOTSTRAP):
            j = rng.integers(0, len(idx), len(idx))
            r = correlation(xb[j], yb[j])
            tirage_rho.append(r)
            tirage_corr.append(correction(r, delta_relatif(xb[j].var(), var_pleine)))
        bas, haut = np.percentile(tirage_rho, [2.5, 97.5])
        cbas, chaut = np.percentile(tirage_corr, [2.5, 97.5])
        tranches.append({
            "n": len(idx), "delta": delta, "rho": rho,
            "rho_corrigee": correction(rho, delta),
            "amplitude_mediane": float(np.median(np.abs(xb))),
            "ic_bas": float(bas), "ic_haut": float(haut),
            "ic_corr_bas": float(cbas), "ic_corr_haut": float(chaut),
        })
    return tranches
