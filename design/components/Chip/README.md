# Chip

La chip est un filtre ou une catégorie que l'on bascule d'un pouce ; actives, elles passent en `indigo`.

## Usage

- Rangée horizontale `sg-chips` qui défile sans barre de défilement, marge `space-4`, écart `space-2`. La rangée fait 56 px de haut : la cible reste de `touch-min` même si la chip mesure 40 px.
- Une chip est un `<button type="button" aria-pressed="…">` ; en htmx, chaque bascule recharge la grille de résultats.
- Icône Lucide de 16 px facultative devant le mot. Deux mots au plus par chip.
- Sur l'accueil : les catégories de premier niveau. Sur les résultats : les filtres actifs en tête (chip active avec une croix pour retirer), puis les suggestions.

## À éviter

Pas de chip pour une action (c'est un bouton), pas de chip rouge ou verte pour un état (c'est un badge).
