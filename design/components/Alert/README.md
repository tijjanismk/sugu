# Alert

L'alerte confirme ou explique en une phrase, en haut de la page ou sous l'action concernée, avec le mot et l'icône qui portent le sens.

## Variantes

- `sg-alert--success` : « Annonce publiée », « Message envoyé ». Icône coche en `success`.
- `sg-alert--danger` : « Impossible de publier » suivi de la cause et du remède. Icône alerte en `danger`.
- `sg-alert--info` : rappel utile (« Les acheteurs ne voient votre numéro qu'une fois connectés »). Icône bouclier ou info en `indigo`.

## Règles

- Titre en `<strong>` coloré, corps en `ink` : seul le titre et l'icône prennent la couleur, pour rester lisible dans les deux thèmes.
- Les messages Django (`messages` framework) se rendent avec ces classes en tête de page, sous la barre du haut, et disparaissent au prochain chargement. Pas de toast flottant qui se ferme seul : sur une connexion lente, on le rate.
- Une alerte de succès après un dépôt propose la suite : « Voir l'annonce ».
