# Badge

Le badge qualifie une annonce en un mot : nouveau, vendu, mode de règlement ; il informe, il ne se touche pas.

## Variantes

- `sg-badge--new` « Nouveau » : annonce de moins de 24 h, `indigo` sur `indigo-soft`.
- `sg-badge--sold` « Vendu » : `surface` sur `ink`.
- `sg-badge--money` « Mobile money » : `ink` sur `sun-soft`, avec l'icône téléphone. « Paiement à la livraison » en badge neutre.
- `sg-badge--drop` « Prix en baisse » : `success` sur `success-soft`, avec la flèche vers le bas. Baisse de prix depuis moins de 14 jours ; l'ancien prix barré (`sg-was`) suit le prix.
- `sg-badge--ok` « Téléphone vérifié » : `success` sur `success-soft`, avec la coche. Réservé à la future vérification OTP.
- Badge neutre (`sg-badge` seul) : catégorie, nombre de photos.

## Règles

- 22 px de haut, texte `caption` en 600, `radius-sm`. Un ou deux mots.
- Sur une carte : un seul badge, en haut à gauche de la photo. Sur la page de l'annonce : une rangée sous le prix, écart `space-2`.
- La couleur n'est jamais le seul signal : chaque badge porte son mot.
