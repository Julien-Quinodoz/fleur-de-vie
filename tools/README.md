# Outils

`build_geometry.py` reconstruit `assets/geometry.js` (cellules/pièces, cercles rotatifs, pas de rotation vérifié, permutations) à partir du modèle `model.py` (motif fleur de vie sur un réseau de pas h = R/2) et échantillonne la couleur de chaque pièce sur l'artwork d'origine :

    python tools/build_geometry.py chemin/vers/enigme10.png   # nécessite numpy, scipy, scikit-image, Pillow
