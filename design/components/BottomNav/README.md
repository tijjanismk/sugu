# BottomNav

La barre basse tient les cinq destinations de premier niveau sous le pouce, avec « Déposer » en `sun` au centre ; c'est le seul élément de l'écran qui porte `shadow-float`.

## Usage

- `<nav class="sg-bottomnav" aria-label="Navigation principale">` fixée en bas, présente sur Accueil, Recherche, Favoris, Messages et Profil. Absente dans un flux (dépôt, conversation ouverte, modification), remplacé par l'action du flux.
- Chaque entrée est un lien `sg-bottomnav__item` : icône Lucide 24 px au-dessus d'un mot en `caption`. La page courante porte `aria-current="page"` et passe en `indigo`.
- « Déposer » est un `sg-bottomnav__post` : disque `sun` de 56 px, bordé de `surface-raised`, qui dépasse la barre de 18 px, avec le mot dessous.
- Messages non lus : pastille `sg-bottomnav__count` en `danger`, nombre jusqu'à 99.
- Respectez `env(safe-area-inset-bottom)` en bas de la barre.
- À partir de 1024 px, la barre devient une barre haute : mêmes liens à gauche, « Déposer une annonce » en `sg-btn--sun` à droite.
