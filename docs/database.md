# Schéma de base de données — Sugu

Toutes les tables ont `id` (clé primaire), `created_at`, `updated_at`.

## accounts_user (modèle utilisateur personnalisé, dès la première migration)

Pas de `username` ni de `first_name` / `last_name` : l'email est l'identifiant (ticket #3,
migration `accounts.0002`). Les tables `account_emailaddress` et
`account_emailconfirmation` d'allauth suivent les adresses et leur confirmation.

| Champ               | Type            | Notes                                       |
|---------------------|-----------------|---------------------------------------------|
| email               | varchar, unique | identifiant de connexion                    |
| password            | varchar         | haché par Django (Argon2)                   |
| display_name        | varchar(50)     | nom affiché sur les annonces, obligatoire   |
| phone               | varchar(20)     | facultatif, chiffres seuls (+ indicatif), visible aux connectés |
| phone_verified      | bool            | réservé à une future vérification OTP       |
| city_id             | FK → city       | optionnel, SET NULL si la ville disparaît   |
| notify_messages     | bool, défaut vrai | email de nouveau message (#12), au profil |
| session_version     | int, défaut 0   | +1 = toutes les sessions tombent (#13)      |
| deleted_at          | timestamp, null | compte supprimé (anonymisé) par son titulaire |
| is_active, is_staff | bool            | Django                                      |

## django_cache

Table du cache Django (`DatabaseCache`), créée par la migration `core.0001` : compteurs de
la limitation de débit d'allauth, partagés entre les processus Gunicorn (pas de Redis en V1).
Dev et tests utilisent un cache en mémoire à la place.

## listings_category

Données de référence chargées par `manage.py seed` (`apps/listings/seed_data.py`, idempotent,
clé = slug) : 10 catégories principales et 20 sous-catégories.

| Champ     | Type                    | Notes                                                  |
|-----------|-------------------------|--------------------------------------------------------|
| name      | varchar(60)             |                                                        |
| slug      | varchar(80), unique     | tiré du nom sans accents ; préfixé du parent si pris   |
| parent_id | FK → category, nullable | PROTECT ; deux niveaux maximum (vérifié à `save()`)    |
| icon      | varchar(40)             | nom d'icône Lucide (catégories principales)            |
| order     | int                     | ordre d'affichage                                      |

Contrainte `category_not_its_own_parent` : CHECK `parent_id <> id`.

## listings_city

Principales villes du Mali chargées par `manage.py seed` (régions du découpage de 2023).

| Champ  | Type                | Notes                       |
|--------|---------------------|-----------------------------|
| name   | varchar(80)         |                             |
| region | varchar(80)         | facultatif                  |
| slug   | varchar(80), unique | tiré du nom sans accents    |

## listings_listing

Statut et prix ne s'écrivent que par `apps/listings/services.py` (`change_status`, `publish`,
`mark_sold`, `remove`, `update_price`, et pour le vendeur `update_listing`,
`seller_mark_sold`, `seller_remove`) ; l'admin les affiche en lecture seule. « Supprimer »
pour le vendeur = statut `removed` : rien n'est effacé, ni la ligne ni les photos.

| Champ            | Type             | Notes                                                       |
|------------------|------------------|-------------------------------------------------------------|
| user_id          | FK → user        | vendeur ; PROTECT (un compte est anonymisé, pas supprimé)   |
| category_id      | FK → category    | PROTECT                                                     |
| city_id          | FK → city        | PROTECT                                                     |
| neighborhood     | varchar(80)      | quartier ou commune, facultatif (ajout du 2026-10-14)       |
| distance_km      | smallint, null   | distance de la ville, 1 à 300 km (CHECK `listing_distance_km_range`) |
| title            | varchar(80)      |                                                             |
| description      | text             | max 2 000 caractères (validation et CHECK)                  |
| price            | integer ≥ 0      | en FCFA, nullable (« à débattre »)                          |
| previous_price   | integer ≥ 0, null| prix affiché juste avant une baisse (ticket #6, 2026-10-14) |
| price_dropped_at | timestamp, null  | date de la baisse ; mention « Prix en baisse » 14 jours     |
| payment_methods  | varchar(20)[]    | valeurs : `cash_on_delivery`, `mobile_money` (CHECK)        |
| status           | varchar(12)      | `draft`, `published`, `reserved`, `sold`, `removed` (CHECK) ; `reserved` inutilisé en V1 |
| search_vector    | tsvector         | maintenu par trigger, index GIN ; ne jamais l'écrire en Python |
| published_at     | timestamp, null  | fixé à la première publication                              |

Index : (status, published_at desc) `listing_status_published_idx`, (category_id), (city_id),
GIN(search_vector) `listing_search_vector_gin`.

Lieu affiché (`Listing.place_label`) : « Sabalibougou, Bamako », « À 20 km de Bamako »,
« Moribabougou, à 20 km de Bamako ».

Contraintes CHECK : `listing_status_valid`, `listing_distance_km_range`, `listing_payment_methods_valid`,
`listing_description_max_length`, `listing_published_has_date` (published / reserved / sold
⇒ `published_at` renseigné), `listing_price_drop_coherent` (`previous_price` et
`price_dropped_at` ensemble, et `previous_price > price`).

Transitions de statut autorisées (`models.ALLOWED_TRANSITIONS`) :

| De          | Vers                          |
|-------------|-------------------------------|
| `draft`     | `published`, `removed`        |
| `published` | `sold`, `removed`             |
| `reserved`  | `published`, `sold`, `removed` (V2) |
| `sold`      | `removed`                     |
| `removed`   | — (définitif)                 |

Recherche plein texte (migrations `listings.0003` et `0005`) : extension `unaccent`,
configuration `french_unaccent` (copie de `french` avec `unaccent` avant `french_stem`), et
trigger `listings_listing_search_vector_trigger` (BEFORE INSERT OR UPDATE OF title,
description, neighborhood) : titre en poids A, quartier en poids B, description en poids C.
La recherche utilise la même configuration (`models.SEARCH_CONFIG`) ; voir
`services.search_listings`.

## listings_photo

| Champ         | Type          | Notes                                              |
|---------------|---------------|----------------------------------------------------|
| listing_id    | FK → listing  | suppression en cascade                             |
| large         | varchar(255)  | `listings/<id>/<uuid>-1200.webp` (R2 en prod)       |
| thumb         | varchar(255)  | `listings/<id>/<uuid>-400.webp`, recadrée 400×300   |
| order         | smallint 0–5  | la photo 0 est la couverture                       |
| width, height | smallint      | pour réserver l'espace à l'affichage               |

Contraintes : unique (listing_id, order) `photo_unique_order` ; CHECK order < 6
`photo_order_max` (6 photos au plus). Supprimer une photo (ou l'annonce, par cascade) efface
ses deux fichiers après validation de la transaction (`apps/listings/signals.py`). Le vendeur
retire une photo par `services.remove_photo` : les suivantes sont renumérotées (la suivante
devient la couverture) et une annonce garde au moins une photo.

## messaging_conversation

| Champ           | Type            | Notes                                            |
|-----------------|-----------------|--------------------------------------------------|
| listing_id      | FK → listing    | protégé : une annonce se retire, ne s'efface pas |
| buyer_id        | FK → user       | protégé : un compte s'anonymise (#13)            |
| seller_id       | FK → user       | dénormalisé pour les requêtes                    |
| last_message_at | timestamp, null | tri de la boîte de réception, indexé             |

Contrainte unique : (listing_id, buyer_id). Contrainte CHECK : buyer_id ≠ seller_id (un
vendeur ne s'écrit pas à lui-même, vérifié aussi par le service). La conversation n'est
créée qu'avec son premier message.

## messaging_message

| Champ           | Type              | Notes                |
|-----------------|-------------------|----------------------|
| conversation_id | FK → conversation |                      |
| sender_id       | FK → user         |                      |
| body            | text              | max 1 000 caractères |
| created_at      | timestamp         |                      |
| read_at         | timestamp, null   | posé à l'ouverture   |

Index : (conversation_id, created_at). Le compteur de non-lus compte les messages reçus
sans `read_at` (une requête par page, processeur de contexte paresseux) ; la boîte de
réception lit dernier message et non-lus de chaque conversation en une requête.

## favorites_favorite

| Champ      | Type                                 |
|------------|--------------------------------------|
| user_id    | FK → user, suppression en cascade    |
| listing_id | FK → listing, suppression en cascade |
| created_at | timestamp                            |

Contrainte unique : (user_id, listing_id). « Mes favoris » trie par `created_at`
décroissant. Les cœurs d'une page sont lus en une requête (identifiants des favoris de
l'utilisateur, processeur de contexte paresseux), quel que soit le nombre de cartes.

## Évolutions prévues (hors V1)

- Table `listings_reservation` pour la réservation (V2) : `listing_id`, `buyer_id`,
  `conversation_id`, `status` (`requested`, `accepted`, `refused`, `cancelled`, `expired`),
  `expires_at`, `created_at`. Contrainte : une seule réservation `accepted` par annonce.
  Le statut `reserved` de l'annonce est dérivé de cette table.
- `listings_listing.boosted_until` pour les mises en avant payantes
- Table `moderation_report` (signalements)
- Table `payments_*` si le paiement intégré est retenu
