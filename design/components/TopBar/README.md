# TopBar

La barre du haut porte le nom « Sugu » sur l'accueil et, ailleurs, le retour, le titre de la page et une action au plus.

## Variantes

- Accueil : marque `sg-topbar__brand` en `indigo`, pilule de lieu `sg-topbar__place` (« Bamako », ouvre le choix de la ville), icône messagerie à droite.
- Page : bouton retour `sg-btn--icon` (icône flèche, `aria-label="Retour"`), titre `sg-topbar__title` en `heading` coupé par des points de suspension, une action à droite (« Modifier », partage).
- Flux de dépôt : titre « Déposer une annonce », retour qui demande confirmation si le formulaire est rempli.

## Règles

- Fond `surface` sur l'accueil ; `sg-topbar--raised` (fond `surface-raised`, filet `line`) quand la page défile sous elle.
- 56 px de haut, marge `space-4`. Pas de logo image : le nom en plain type est le logo tant qu'une marque dessinée n'existe pas.
