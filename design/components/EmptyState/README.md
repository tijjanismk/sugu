# EmptyState

Un écran vide invite à agir : un disque `indigo-soft` avec l'icône du sujet, une phrase de titre, une phrase d'explication et, si une action existe, un bouton.

## Usage

- `sg-empty` centré, marge haute `space-8`, texte sur 30 caractères par ligne au plus.
- Titre en `heading`, constat sans drame : « Aucun favori pour l'instant ». Texte en `small` `ink-muted` qui dit comment remplir l'écran.
- Bouton : `sg-btn--primary` pour mener à l'action (« Chercher une annonce »), `sg-btn--sun` seulement si l'action est le dépôt d'une annonce (« Mes annonces » vide).
- Résultats de recherche vides : proposez d'élargir (« Retirer les filtres », « Chercher dans tout le Mali ») plutôt qu'un simple constat.
- Jamais d'illustration ni d'émoji : l'icône Lucide du sujet suffit.
