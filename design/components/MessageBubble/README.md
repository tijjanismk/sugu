# MessageBubble

La conversation entre acheteur et vendeur se lit comme une messagerie de téléphone : mes messages en `indigo` à droite, les siens sur `surface-raised` à gauche.

## Anatomie

- `sg-thread` empile les bulles avec `space-2`, marge `space-4` ; un séparateur de jour `sg-thread__day` en `caption` (« Aujourd'hui », « Hier », « 12 oct. »).
- `sg-msg` : 78 % de large au plus, `radius-lg`, coin inférieur côté auteur en `radius-sm`. Texte en 15 px.
- `sg-msg--me` : fond `indigo`, texte `on-indigo`. Heure et double coche de lecture dans `sg-msg__time` ; coche simple = envoyé, double = lu.
- Le compositeur `sg-composer` est collé en bas : champ pilule de `touch-min`, bouton `sg-btn--primary sg-btn--icon` avec l'icône envoyer.

## Règles

- En tête de conversation, la carte de l'annonce concernée en version compacte (photo 56 px, prix, titre), lien vers l'annonce.
- Rafraîchissement par htmx toutes les 10 s quand la conversation est ouverte ; les nouveaux messages s'ajoutent sans recharger.
- Un message fait 1 000 caractères au plus ; les liens sont cliquables, rien d'autre n'est interprété.
