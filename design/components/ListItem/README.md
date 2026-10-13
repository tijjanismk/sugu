# ListItem

La ligne de liste sert aux conversations et à « Mes annonces » : une vignette ou un avatar, un titre, une ligne de texte, l'heure à droite.

## Usage

- `sg-list` est une `<ul>` ; chaque `sg-list__item` est un lien de `touch-min` au moins (56 px ici), séparé par un filet `line`.
- Conversation : avatar 40 px, nom du correspondant en `sg-list__title`, dernier message en `sg-list__text`, heure relative en `sg-list__time`. Non lue : `sg-list__item--unread`, texte en `ink` et point `sg-dot` en `indigo` à droite.
- Mes annonces : vignette 56 px, titre, « 45 000 FCFA · 12 vues » et le badge de statut.
- Pas de bouton dans la ligne : la ligne entière est le lien ; les actions sont sur la page ouverte.
