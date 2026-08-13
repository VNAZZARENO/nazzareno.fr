"""Exporte des valeurs de reference de limb.py, pour verifier que le miroir
JavaScript calcule exactement la meme chose.

A lancer depuis la racine du depot:
    source .venv/bin/activate && python3 -m tools.eclipse.export_flux_lut
"""

import json
import pathlib

from tools.eclipse.limb import SRGB_LIMB_COEFFS, visible_flux_fraction

SORTIE = pathlib.Path(__file__).resolve().parents[2] / "tools/js-tests/flux-reference.json"

CAS = [(d, ratio)
       for d in (0.0, 0.1, 0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 1.9, 2.05)
       for ratio in (0.92, 1.0, 1.05)]


def main():
    SORTIE.write_text(json.dumps({
        "coeffs": [list(c) for c in SRGB_LIMB_COEFFS],
        "n": 512,
        "cases": [
            {"d": d, "rMoon": ratio,
             "flux": [visible_flux_fraction(d, 1.0, ratio, u1, u2, n=512)
                      for u1, u2 in SRGB_LIMB_COEFFS]}
            for d, ratio in CAS
        ],
    }, indent=1))
    print(f"ecrit {SORTIE} ({len(CAS)} cas)")


if __name__ == "__main__":
    main()
