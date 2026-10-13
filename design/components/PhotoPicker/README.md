# PhotoPicker

Le sélecteur de photos du dépôt d'annonce : une grille de tuiles carrées, la première marquée « Couverture », et une tuile pointillée « Ajouter » tant qu'il reste de la place.

## Usage

- `sg-photos` : trois colonnes, écart `space-2`. Six photos au plus, 8 Mo chacune ; la tuile « Ajouter » disparaît à la sixième.
- La tuile `sg-photo--add` est un `<button>` qui ouvre `<input type="file" accept="image/*" capture="environment" multiple>` : sur téléphone, l'appareil photo s'ouvre directement.
- Chaque photo choisie s'affiche en aperçu local (`URL.createObjectURL`) avant l'envoi ; la croix `sg-photo__remove` la retire.
- La première tuile porte `sg-photo__cover` : c'est elle qui apparaît sur la carte. L'ordre se change par glisser-déposer en V2 ; en V1, une photo retirée puis rajoutée passe en dernier.
- Pendant l'envoi : un `Skeleton` à la place de la tuile ; en cas d'échec : `Alert` danger « Photo trop lourde (12 Mo). 8 Mo au plus. ».
- Aide sous la grille : « La première photo est la couverture. Prenez-la en plein jour, sur fond simple. »
