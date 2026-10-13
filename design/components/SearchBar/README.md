# SearchBar

Le champ de recherche est la porte d'entrée de l'accueil : une pilule `surface-sunken` qui devient `surface-raised` bordée d'`indigo` au focus, avec le bouton des filtres à sa droite.

## Comportement

- Formulaire GET vers la page de résultats, champ `q` ; les filtres (catégorie, ville, prix) restent dans l'URL pour qu'un résultat se partage.
- Saisie en 16 px : le téléphone ne zoome pas. Le placeholder dit quoi chercher : « Que cherchez-vous ? ».
- Le bouton effacer (`sg-search__clear`) n'apparaît que si le champ a du texte.
- Le bouton filtres (`sg-btn sg-btn--icon`) ouvre la feuille de filtres ; quand des filtres sont actifs, affichez le nombre dans un `sg-badge--new` à côté.
- Sur la page de résultats, la barre est collée en haut (`position: sticky`) sur fond `surface`.

## À fournir

Le texte courant du champ, le nombre de filtres actifs, l'URL de la feuille de filtres.
