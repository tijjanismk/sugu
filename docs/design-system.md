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
`empty_state`, `icon` (tracés Lucide), puis `category_tiles` (#5) et `field` (#7 : champ,
liste déroulante, suffixe « FCFA », cases à cocher) ; les autres composants arrivent avec le ticket qui
les utilise. Poids de l'accueil mesuré : 45 Ko compressés (HTML, CSS, htmx et police).

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
