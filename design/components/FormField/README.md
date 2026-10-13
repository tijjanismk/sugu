# FormField

Un champ de formulaire est un libellé en `small-strong`, un contrôle de 48 px bordé de `line-strong`, et une ligne d'aide ou d'erreur ; il se lit et se remplit d'une main.

## Anatomie

- `sg-field` empile le libellé, le contrôle et l'aide avec 6 px d'écart, marge latérale `space-4`.
- Libellé : `<label for>` obligatoire ; la mention « facultatif » en `<small>` après le mot, jamais un astérisque pour l'obligatoire.
- Contrôle : `sg-input` sur `<input>`, `<textarea>` (112 px minimum, redimensionnable) ou `<select>` dans un `sg-select` avec son chevron.
- Prix : `sg-input sg-input--prefix` avec l'unité « FCFA » à droite, `inputmode="numeric"`. Téléphone : `type="tel"`, `inputmode="tel"`.
- Aide : `sg-field__help` en `ink-muted`, une phrase utile (« 6 photos au plus, 8 Mo chacune »).
- Erreur : `sg-field--error` sur le conteneur, message `sg-field__error` avec l'icône, relié par `aria-describedby`, et le focus posé sur le premier champ en erreur après soumission.

## Règles

- 16 px de texte dans le contrôle : le téléphone ne zoome pas.
- Un formulaire = une colonne, dans `content-max`. Le bouton de validation est collé en bas (`sg-sticky`), en `sg-btn--primary sg-btn--lg sg-btn--block`.
- Cases à cocher et modes de règlement : `sg-check`, ligne de `touch-min`, case de 22 px en `indigo`.
- Validation côté serveur par Django ; htmx renvoie le formulaire avec ses erreurs sans recharger la page.
