# Skeleton

Le squelette réserve exactement la place du contenu qui arrive, en `surface-sunken` qui pulse doucement ; sur une connexion lente, il vaut mieux qu'un spinner.

## Usage

- Carte annonce : un bloc média 4:3 puis trois lignes (prix 40 %, titre 90 %, lieu 60 %) aux mêmes marges que la vraie carte.
- Liste de conversations : avatar rond 40 px, deux lignes.
- Utilisé par htmx avec `hx-indicator` sur la grille pendant « Voir plus », et comme contenu initial de la grille si la page est servie avant les annonces.
- `prefers-reduced-motion` : le squelette ne pulse pas.
- Durée : si le contenu n'arrive pas en 10 s, remplacez par une `Alert` danger avec un bouton « Réessayer ».
