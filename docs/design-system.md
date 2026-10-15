# Design system — Sugu

La charte graphique et la bibliothèque de composants vivent dans deux endroits
qui doivent rester synchronisés :

- **L'artefact « Sugu — Design System »** sur claude.ai : la version navigable
  (tokens par thème, aperçus en direct, guides d'usage). C'est là qu'on
  discute et qu'on modifie la charte.
- **Le dossier `design/` de ce dépôt** : la copie de référence commitée.
  - `design/README.md` — la charte (principes, contenu, couleurs, typographie,
    mise en page, iconographie, états). À fournir à l'IA avec `CONTEXT.md`
    pour toute tâche qui touche à l'interface.
  - `design/tokens.json` — la source des tokens (couleurs clair/sombre, styles
    de texte, espacements, rayons, ombre, dimensions).
  - `design/tokens.css` — généré depuis `tokens.json` : variables CSS par
    thème (`:root` / `[data-theme="dark"]`) et une classe par style de texte.
  - `design/components/bundle.css` — les classes `sg-…` de tous les composants.
  - `design/components/<Composant>/` — `README.md` (règles d'usage) et
    `preview.html` (exemple HTML à transposer en gabarit Django).

## Règle de synchronisation

Toute modification de la charte se fait d'abord dans l'artefact, puis est
recopiée dans `design/` dans la même PR que le code qui l'utilise. Le fichier
`tokens.css` est regénéré, jamais édité à la main.

## Traduction en code (ticket #4)

Fait au ticket #4 : `static/css/tokens.css`, `static/css/components.css` (rangés dans les
couches `base` et `components` de Tailwind, pour qu'une classe utilitaire l'emporte),
`@theme inline` dans `input.css`, Figtree servie localement, barre haute à partir de 1024 px
(`sg-topnav`). Gabarits créés : `top_bar`, `bottom_nav`, `alert`, `messages`,
`empty_state`, `icon` (tracés Lucide), puis `category_tiles` (#5), `field` (#7 : champ,
liste déroulante, suffixe « FCFA » ou « km », cases à cocher) et `listing_card` (#8).

Ajouts du ticket #8 dans `design/` (à reporter dans l'artefact de design) : badge
`sg-badge--drop` « Prix en baisse », ancien prix barré `sg-was`, grille à 3 puis 4 colonnes
(640 et 1024 px), galerie `sg-gallery` de la page annonce, et règle du lieu hors de la ville
dans `design/README.md`. Ticket #9 : chip active en lien `sg-chip--on`, ancien prix sur sa
propre ligne dans une carte (il débordait), composant `search_bar`. Ticket #10 : vignette
`sg-list__thumb` de ListItem pour « Mes annonces ». Ticket #11 : conteneur `sg-card-slot`
(carte + bouton favori frère, la carte garde la hauteur de la rangée) et cœur `sg-fav` dans
la barre du haut de la page annonce. Ticket #12 : lien dans une bulle `.sg-msg a`, icônes
`send` et `read` (double coche). Ticket #13 : icône `phone`, ligne vendeur `sg-seller` sur
l'annonce et en tête du profil. Ticket #14 : icône d'application (« S » Figtree ExtraBold
blanc sur `indigo`, point `sun`), générée par `scripts/make_icons.py` dans
`static/img/icons/` (à reporter dans l'artefact de design) ; page hors-ligne sur le modèle
EmptyState. Bannière « Installer l'application » (#14, 2026-10-15) : Alert info avec
icône `smartphone` et deux boutons (`sg-btn--primary` « Installer », `sg-btn--quiet` « Plus
tard ») sous la barre de recherche de l'accueil (à reporter dans l'artefact de design).
Pages catégorie et ville (#9, 2026-10-15) : fil d'Ariane en `caption`, titre, compteur,
grille de cartes, liens vers les pages voisines en `sg-chip` ; la page annonce reprend ces
chips sous « Plus d'annonces » ; pages légales et « À propos » (#17, 2026-10-15) : texte long
`sg-prose` (titres en styles `title` et `heading`, texte `body`, date en `ink-muted`) et pied
de page `sg-footer` (liens en `ink-muted`, zones tactiles de 44 px, filet `line`), absent des
parcours (dépôt, modification, conversation, confirmation) ; à reporter dans l'artefact de
design ; les autres composants arrivent avec le ticket qui les utilise. Poids de l'accueil mesuré : 45 Ko compressés (HTML, CSS, htmx et police).

1. `static/css/tokens.css` ← copie de `design/tokens.css`.
2. `static/css/input.css` : `@import "tailwindcss";` puis un bloc `@theme` qui
   expose les tokens à Tailwind 4 (`--color-indigo: var(--indigo);`,
   `--radius-md: 10px;`, `--font-sans: …`), pour écrire `bg-indigo`,
   `text-ink-muted`, `rounded-md` dans les gabarits.
3. `static/css/components.css` ← `design/components/bundle.css` (sans la ligne
   `@import` Google Fonts : la police est servie localement en sous-ensemble
   latin, `font-display: swap`).
4. `templates/components/` : un gabarit par composant, repris de
   `design/components/<Composant>/preview.html` (`button.html`,
   `listing_card.html`, `search_bar.html`, `chip.html`, `field.html`,
   `bottom_nav.html`, `top_bar.html`, `badge.html`, `message.html`,
   `empty_state.html`, `alert.html`, `skeleton_card.html`, `category_tile.html`,
   `avatar.html`, `photo_picker.html`, `list_item.html`).
5. Thème : `<html data-theme="…">` posé par un petit script inline qui lit
   `prefers-color-scheme` puis le choix enregistré dans le profil.

## Composants (16)

Button, ListingCard, SearchBar, Chip, FormField, PhotoPicker, BottomNav,
TopBar, CategoryTile, Badge, MessageBubble, ListItem, Avatar, EmptyState,
Alert, Skeleton.
