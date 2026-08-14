"""La formule de Forbes et Rigobon (2002), et son inversion.

Modele y = a + b*x + e, e independant de x et homoscedastique. Conditionner
sur un evenement defini sur x seul ne change pas b, seulement le rapport
signal sur bruit: la correlation d'echantillon monte avec la variance de x
sans qu'aucun parametre structurel n'ait bouge. C'est tout le sujet de la
page; ces trois fonctions sont les seules formules du projet.
"""
import math


def delta_relatif(var_sous_echantillon, var_pleine):
    """L'exces relatif de variance du sous-echantillon, le delta de la formule."""
    return var_sous_echantillon / var_pleine - 1.0


def rho_conditionnelle(rho, delta):
    """Correlation d'echantillon attendue sous conditionnement, a rho vrai constant."""
    return rho * math.sqrt(1.0 + delta) / math.sqrt(1.0 + delta * rho * rho)


def correction(rho_cond, delta):
    """L'inversion: retrouve la correlation non conditionnelle. C'est la correction F-R."""
    return rho_cond / math.sqrt(1.0 + delta * (1.0 - rho_cond * rho_cond))
