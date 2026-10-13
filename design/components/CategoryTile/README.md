# CategoryTile

La tuile de catégorie est un carré `indigo-soft` de 56 px avec l'icône de la catégorie en `indigo` et son nom dessous ; la grille d'accueil en montre huit.

## Usage

- `sg-cats` : grille de quatre colonnes, écart `space-2`, marge `space-4`. Deux rangées sur l'accueil, puis « Toutes les catégories » en `sg-btn--quiet`.
- Chaque tuile est un lien vers la recherche filtrée sur la catégorie. Nom en `caption` 500, un ou deux mots, pas de troncature : choisissez des noms courts (« Téléphones », pas « Téléphonie et accessoires »).
- Les icônes viennent de Lucide (`smartphone`, `car`, `home`, `shirt`, `armchair`, `wrench`, `bike`, `laptop`) ; le champ `icon` du modèle `Category` porte ce nom.
- Sur la page d'une catégorie, ses sous-catégories s'affichent en `Chip`, pas en tuiles.
