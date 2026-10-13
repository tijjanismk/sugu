# Schéma de base de données — Sugu

Toutes les tables ont `id` (clé primaire), `created_at`, `updated_at`.

## accounts_user (modèle utilisateur personnalisé, dès la première migration)

| Champ               | Type            | Notes                                 |
|---------------------|-----------------|---------------------------------------|
| email               | varchar, unique | identifiant de connexion              |
| password            | varchar         | haché par Django                      |
| display_name        | varchar(50)     | nom affiché sur les annonces          |
| phone               | varchar(20)     | contact, visible aux connectés        |
| phone_verified      | bool            | réservé à une future vérification OTP |
| city_id             | FK → city       | optionnel                             |
| is_active, is_staff | bool            | Django                                |

## listings_category

| Champ     | Type                    | Notes                 |
|-----------|-------------------------|-----------------------|
| name      | varchar(60)             |                       |
| slug      | varchar, unique         |                       |
| parent_id | FK → category, nullable | deux niveaux maximum  |
| icon      | varchar(40)             | nom d'icône           |
| order     | int                     | ordre d'affichage     |

## listings_city

| Champ  | Type            | Notes |
|--------|-----------------|-------|
| name   | varchar(80)     |       |
| region | varchar(80)     |       |
| slug   | varchar, unique |       |

## listings_listing

| Champ           | Type            | Notes                                        |
|-----------------|-----------------|----------------------------------------------|
| user_id         | FK → user       | vendeur                                      |
| category_id     | FK → category   |                                              |
| city_id         | FK → city       |                                              |
| title           | varchar(80)     |                                              |
| description     | text            | max 2 000 caractères                         |
| price           | integer         | en FCFA, nullable (« à débattre »)           |
| payment_methods | varchar[]       | valeurs : `cash_on_delivery`, `mobile_money` |
| status          | varchar(12)     | `draft`, `published`, `reserved`, `sold`, `removed` (`reserved` inutilisé en V1, réservé à la V2) |
| search_vector   | tsvector        | maintenu par trigger, index GIN              |
| published_at    | timestamp, null |                                              |

Index : (status, published_at desc), (category_id), (city_id), GIN(search_vector)

## listings_photo

| Champ         | Type         | Notes                                |
|---------------|--------------|--------------------------------------|
| listing_id    | FK → listing | suppression en cascade               |
| large         | varchar      | clé R2 de la version 1200 px WebP    |
| thumb         | varchar      | clé R2 de la miniature 400 px WebP   |
| order         | smallint     | la photo 0 est la couverture         |
| width, height | smallint     | pour réserver l'espace à l'affichage |

## messaging_conversation

| Champ      | Type         | Notes                         |
|------------|--------------|-------------------------------|
| listing_id | FK → listing |                               |
| buyer_id   | FK → user    |                               |
| seller_id  | FK → user    | dénormalisé pour les requêtes |

Contrainte unique : (listing_id, buyer_id)

## messaging_message

| Champ           | Type              | Notes                |
|-----------------|-------------------|----------------------|
| conversation_id | FK → conversation |                      |
| sender_id       | FK → user         |                      |
| body            | text              | max 1 000 caractères |
| read_at         | timestamp, null   |                      |

Index : (conversation_id, created_at)

## favorites_favorite

| Champ      | Type         |
|------------|--------------|
| user_id    | FK → user    |
| listing_id | FK → listing |

Contrainte unique : (user_id, listing_id)

## Évolutions prévues (hors V1)

- Table `listings_reservation` pour la réservation (V2) : `listing_id`, `buyer_id`,
  `conversation_id`, `status` (`requested`, `accepted`, `refused`, `cancelled`, `expired`),
  `expires_at`, `created_at`. Contrainte : une seule réservation `accepted` par annonce.
  Le statut `reserved` de l'annonce est dérivé de cette table.
- `listings_listing.boosted_until` pour les mises en avant payantes
- Table `moderation_report` (signalements)
- Table `payments_*` si le paiement intégré est retenu
