# ListingCard

La carte annonce montre une photo 4:3, le prix en premier, un titre sur deux lignes et le lieu ; elle est le motif répété de tout Sugu.

## Structure

- La carte entière est un lien `<a class="sg-card">` vers l'annonce. Le bouton favori est un `<button>` frère, positionné dans le coin, jamais imbriqué dans le lien.
- `sg-card__media` : `<img>` WebP 400 px, `width="400" height="300"`, `alt` = titre de l'annonce ; sans photo, un `<div>` avec l'icône appareil photo.
- `sg-card__price` : style `price`, couleur `indigo`, « 45 000 FCFA » ; prix absent : `sg-card__price--open` et « À débattre ».
- `sg-card__title` : style `small`, deux lignes au plus, coupé par `line-clamp`.
- `sg-card__meta` : icône épingle + « Quartier, Ville · il y a 2 h », en `ink-muted`.

## États

- Favori actif : `aria-pressed="true"` sur le bouton, cœur plein en `heart`. La bascule se fait en htmx sur le bouton seul.
- Vendue : `sg-card--sold`, photo atténuée, prix barré en `ink-muted`, badge « Vendu ». La carte reste visible sur la page du vendeur, disparaît de la recherche.
- Nouvelle (moins de 24 h) : badge `sg-badge--new` en haut à gauche.
- Chargement : la carte `Skeleton` de mêmes dimensions.

## Grille

`sg-grid` : deux colonnes, gouttière `space-3`, marge `space-4` ; trois colonnes à partir de 640 px, quatre à 1024 px dans `page-max`. Le bouton « Voir plus » (`sg-btn`, pleine largeur) charge la page suivante en htmx sous la grille.

## Prix sur la page de l'annonce

`sg-price-lg` (style `price-lg`) sous la galerie, suivi des badges de mode de règlement.
