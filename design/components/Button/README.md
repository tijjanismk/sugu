# Button

Le bouton déclenche une action nommée par son libellé ; une seule variante `sun` par écran, pour « Déposer une annonce ».

## Variantes

- `sg-btn--primary` : l'action principale d'un formulaire ou d'une page (Publier, Envoyer, Contacter). Fond `indigo`, texte `on-indigo`.
- `sg-btn--sun` : uniquement « Déposer une annonce ». Fond `sun`, texte `on-sun`.
- `sg-btn` seul : action secondaire (Modifier, Annuler, Voir plus). Bord `line-strong`.
- `sg-btn--quiet` : action discrète dans une barre ou une liste (Passer, Tout voir).
- `sg-btn--danger` : destruction ou retrait (Supprimer l'annonce). Toujours suivi d'une confirmation.

## Tailles et formes

- Hauteur `touch-min` (44 px) par défaut ; `sg-btn--lg` (`touch-lg`, 52 px) pour le bouton collé en bas d'un formulaire et pour « Appeler le vendeur ».
- `sg-btn--block` prend toute la largeur : c'est la règle sur mobile pour l'action principale.
- `sg-btn--icon` : carré de 44 px pour une icône seule, avec un `aria-label` obligatoire.

## États

- En cours : ajoutez `.sg-spinner` avant le libellé et changez le mot (« Publication… ») ; gardez `aria-disabled="true"` le temps de la requête htmx.
- Désactivé : attribut `disabled` ; 50 % d'opacité. Préférez un bouton actif qui explique l'erreur à un bouton grisé sans raison visible.
- Focus clavier : anneau `focus` fourni par la classe, ne le retirez pas.

## À fournir

Un libellé à l'infinitif, en casse de phrase, trois mots au plus ; une icône Lucide facultative avant le texte ; pour un lien stylé en bouton, un `<a>` avec les mêmes classes.
