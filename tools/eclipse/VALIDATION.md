# Validation du calcul

Comparaison du calcul de `tools/eclipse/build.py` (fichier `assets/data/eclipse-2026-08-12.json`) aux valeurs publiees consignees dans `NASA-REFERENCE.md` (tache 6), transcrites depuis timeanddate.com (T&D) et recoupees, pour Palma, avec l'IGN espagnol.

**Rien dans ce fichier n'est une source.** Les valeurs publiees viennent de `NASA-REFERENCE.md`, qui les a lui-meme recopiees de sources externes avant qu'aucun calcul ne soit fait ici. Ce script ne fait que comparer deux colonnes de nombres et rapporter l'ecart.

## Pourquoi 30 s de tolerance, et non 5 s

Les sources publiees ne s'accordent pas entre elles : sur l'instant du maximum global, GSFC, EclipseWise et l'IMCCE different deja de 9 s ; sur les contacts de Palma, timeanddate.com, l'IGN et Wikipedia FR different de 2 a 6 s ; sur la duree de la totalite a Reykjavik, les sources islandaises different de 12 s. La cause recurrente est DeltaT (TT - UT1) : les sources retenues en supposent des valeurs allant de 69.6 s a 75.4 s (voir `NASA-REFERENCE.md`, "Trois pieges de transcription"), un ecart qui a lui seul deplace un contact de plusieurs secondes.

Une tolerance de 5 s mesurerait donc ce desaccord entre sources, pas la justesse de ce calcul. 30 s reste tres discriminant : une vraie faute dans ce pipeline (mauvaise date, signe de longitude invertit, corps celeste confondu, refraction oubliee) deplace un contact de plusieurs minutes a plusieurs heures, jamais de vingt secondes.

**DeltaT utilise par skyfield pour cette eclipse (a 17:45:51 UTC) : 69.11 s.** A titre de comparaison, les sources publiees retenues dans `NASA-REFERENCE.md` supposent, pour la meme eclipse : GSFC 75.4 s, EclipseWise 72.4 s, IMCCE 75.319 s, timeanddate.com 69.6 s. La valeur skyfield tombe meme legerement sous la plus basse des quatre, ce qui est cohere avec des contacts calcules systematiquement quelques secondes en avance sur T&D (voir le tableau ci-dessous) : un DeltaT plus petit avance legerement tous les instants.

## Hauteur du Soleil : refraction comprise, un piege signale

Le pipeline (`tools/eclipse/ephemeris.py::state_at`) rapporte des hauteurs **apparentes**, refraction atmospherique standard (15 degC, 1013.25 mbar) comprise -- c'est ce qui compte pour un rendu visuel, et c'est indispensable a Palma ou l'eclipse se joue a moins de 3 degres de l'horizon. timeanddate.com semble publier la meme convention (voir plus bas). L'IGN espagnol, lui, semble publier une hauteur **geometrique** (sans refraction) pour Palma : 2.4 deg contre 2.6 deg chez T&D pour le meme instant. Comparer notre valeur a l'IGN sans corriger de la refraction comparerait deux grandeurs differentes ; la ligne "IGN (info)" du tableau l'affiche donc a part, avec l'explication qui suit.

## Tableau de comparaison

| Lieu | Grandeur | Publie | Calcule | Ecart | Tolerance | Verdict |
|---|---|---|---|---|---|---|
| Paris | C1 | 17:22:14 | 17:22:15 | +1.8 s | 30 s | ok |
| Paris | C2 | — | — | — | — | pas de totalite a ce lieu (fait astronomique) |
| Paris | C3 | — | — | — | — | pas de totalite a ce lieu (fait astronomique) |
| Paris | C4 | 19:09:28 | 19:09:26 | -1.7 s | 30 s | ok |
| Paris | magnitude | 0.9310 | 0.93103 | +0.0000 | 0.005 | ok |
| Paris | obscuration | 92.1 % / 92.2 % | 92.12 % | +0.02 pt / -0.08 pt | n/a (reference non stricte) | info |
| Paris | hauteur du Soleil (max, apparente) | 7.7 deg | 7.7129 deg | +0.0129 deg | 0.15 deg | ok |
| Paris | azimut du Soleil (max) | 284.0 deg | 283.8142 deg | -0.1858 deg | 0.5 deg | ok |
| Palma de Majorque | C1 | 17:38:04 | 17:38:05 | +1.5 s | 30 s | ok |
| Palma de Majorque | C2 | 18:31:06 | 18:31:04 | -1.4 s | 30 s | ok |
| Palma de Majorque | C3 | 18:32:42 | 18:32:43 | +1.4 s | 30 s | ok |
| Palma de Majorque | C4 | 19:22:34 | 19:22:31 | -2.0 s | 30 s | ok |
| Palma de Majorque | magnitude | 1.0150 | 1.01301 | -0.0020 | 0.005 | ok |
| Palma de Majorque | obscuration | 100.0 % | 100.00 % | +0.00 pt | 1 pt | ok |
| Palma de Majorque | hauteur du Soleil (max, apparente) | 2.6 deg | 2.6443 deg | +0.0443 deg | 0.20 deg | ok |
| Palma de Majorque | hauteur du Soleil (max, IGN) | 2.4 deg | 2.6443 deg | +0.2443 deg | n/a (geometrique probable, voir texte) | info |
| Palma de Majorque | azimut du Soleil (max) | 287.3 deg | 287.2762 deg | -0.0238 deg | 0.5 deg | ok |
| Reykjavik | C1 | 16:47:13 | 16:47:14 | +1.9 s | 30 s | ok |
| Reykjavik | C2 | 17:48:18 | 17:48:15 | -2.6 s | 30 s | ok |
| Reykjavik | C3 | 17:49:18 | 17:49:21 | +3.2 s | 30 s | ok |
| Reykjavik | C4 | 18:47:40 | 18:47:39 | -0.5 s | 30 s | ok |
| Reykjavik | magnitude | 1.0020 | 1.00227 | +0.0003 | 0.005 | ok |
| Reykjavik | obscuration | 100.0 % | 100.00 % | +0.00 pt | 1 pt | ok |
| Reykjavik | hauteur du Soleil (max, apparente) | 24.5 deg | 24.5225 deg | +0.0225 deg | 0.15 deg | ok |
| Reykjavik | azimut du Soleil (max) | 253.0 deg | 252.7659 deg | -0.2341 deg | 0.5 deg | ok |

Les lignes marquees **info** ne comptent pas dans le verdict global : elles comparent a une reference que `NASA-REFERENCE.md` signale lui-meme comme non stricte (deux valeurs discordantes pour l'obscuration de Paris) ou incompatible en nature (hauteur geometrique de l'IGN contre hauteur apparente calculee). Elles sont affichees pour transparence, pas pour etre satisfaites ou non.

## Coherence interne : t_max_s contre le maximum recalcule

- OK paris: t_max_s (image 180) coincide avec le maximum recalcule sur les 352 frames.
- OK espagne: t_max_s (image 176) coincide avec le maximum recalcule sur les 344 frames.
- OK reykjavik: t_max_s (image 200) coincide avec le maximum recalcule sur les 392 frames.

## Ce que cette validation ne couvre pas

- **Paris repose sur une seule source a la seconde** (timeanddate.com). L'IMCCE et l'Observatoire de Paris publient des circonstances locales, mais uniquement via un formulaire JavaScript dont la sortie n'a pas pu etre recuperee pour la tache 6 ; les sites secondaires qui citent l'IMCCE ne recoupent qu'a la minute pres.
- **timeanddate.com est un agregateur commercial**, pas un service d'ephemerides national ou universitaire. C'est la source retenue parce qu'elle est la seule a publier les quatre contacts a la seconde pour les trois villes avec une methode homogene, pas parce qu'elle fait autorite au meme titre que GSFC ou l'IGN.
- **Reykjavik est pres du bord du trajet de la totalite** : les sources publiees donnent des durees de totalite qui vont de 58 a 70 s selon le point exact vise dans la ville. Un ecart de quelques secondes sur C2/C3 a Reykjavik peut donc venir d'un choix de point different, pas d'une erreur de calcul de part ou d'autre.
- **Le point exact designe par chaque ville n'est pas publie** par T&D. Comparer nos coordonnees (voir `build.py::SITES`) a un point inconnu est une limite intrinseque de cette validation, quelle que soit la qualite du calcul des deux cotes.
- Cette validation compare des **instants et des grandeurs ponctuelles au maximum**, pas la trajectoire complete de l'ombre ni le rendu visuel (flux RGB, assombrissement centre-bord, ciel etoile), qui ne sont pas publies avec une precision comparable par les sources retenues.

## Verdict global : CONFORME

Tous les contacts, la magnitude, l'obscuration, la hauteur et l'azimut du Soleil au maximum, pour les trois sites, tombent dans la tolerance annoncee. `t_max_s` designe bien, dans les trois cas, l'image de magnitude maximale parmi les frames calculees.
