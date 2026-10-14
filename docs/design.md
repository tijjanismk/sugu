# Document de conception — Sugu

## 1. Objectif

Permettre à des particuliers de publier et trouver des annonces de biens
d'occasion, puis d'entrer en contact, sur des téléphones d'entrée de gamme et
des connexions lentes. V1 = valider que des utilisateurs publient et se
contactent réellement.

## 2. Utilisateurs et parcours principaux

- **Visiteur** : parcourt et recherche sans compte ; doit créer un compte pour
  contacter un vendeur ou mettre en favori
- **Vendeur** : crée un compte, dépose une annonce avec photos, répond aux
  messages, marque l'annonce comme vendue
- **Acheteur** : recherche, filtre, enregistre des favoris, écrit au vendeur

## 3. Architecture

Monolithe Django rendu côté serveur. Une seule application déployée, une seule
base de données.

```
Navigateur (HTML + htmx + service worker)
        │ HTTPS
   Cloudflare (CDN, cache des fichiers statiques, protection)
        │
   Caddy (TLS, reverse proxy)           VPS Hetzner
        │
   Gunicorn → Django 6.1 ─ PostgreSQL 18
        │
   Cloudflare R2 (photos, servies directement par R2/CDN)
```

Apps Django :

| App        | Responsabilité                                              |
|------------|-------------------------------------------------------------|
| core       | accueil, pages statiques, manifest PWA, service worker      |
| accounts   | modèle utilisateur personnalisé, profil, téléphone          |
| listings   | annonces, catégories, villes, photos, recherche, filtres    |
| messaging  | conversations liées à une annonce, messages                 |
| favorites  | favoris                                                     |

## 4. Flux de données principaux

### Dépôt d'annonce

1. Formulaire Django (titre, description, catégorie, ville, prix,
   modes de règlement, photos)
2. Validation côté serveur ; limite 6 photos, 8 Mo chacune
3. Pour chaque photo : Pillow génère une version 1200 px et une miniature
   400 px en WebP, envoyées sur R2 ; l'original n'est pas conservé
4. Annonce enregistrée avec statut `published` ; vecteur de recherche
   mis à jour par un trigger PostgreSQL

### Recherche

1. Requête GET avec `q`, `category`, `city`, `price_min`, `price_max`, `page`
2. Recherche plein texte PostgreSQL (`search_vector` maintenu par trigger sur titre +
   description, configuration `french_unaccent`) + filtres + tri par date
3. Rendu HTML complet ou partial htmx si en-tête `HX-Request`

### Messagerie

1. Depuis une annonce, l'acheteur ouvre une conversation (unique par
   couple annonce/acheteur)
2. Messages stockés en base ; la page de conversation se rafraîchit par
   htmx polling toutes les 10 s quand elle est ouverte
3. Compteur de non-lus dans l'en-tête

## 5. Performance sur connexion lente

- Aucune dépendance JS externe ; htmx (~14 Ko gzip) servi localement
- CSS Tailwind purgé (< 15 Ko gzip)
- Images toujours en WebP, dimensions fixées pour éviter les sauts de mise en page
- Pagination à 20 annonces, chargement « voir plus » par htmx
- Cache Cloudflare sur `/static/` et les photos R2
- Objectif : page d'accueil < 100 Ko transférés hors photos

## 6. Sécurité et données personnelles

- Mots de passe hachés par Django (Argon2)
- Numéro de téléphone visible uniquement aux utilisateurs connectés
- CSRF, en-têtes de sécurité et HTTPS forcés en production
- Suppression de compte : anonymisation des annonces et messages
- Pas de données de paiement stockées

## 7. Alternatives écartées

| Alternative              | Raison du rejet                                            |
|--------------------------|------------------------------------------------------------|
| Go + htmx                | Plus de code à écrire soi-même ; V1 plus lente à livrer    |
| SvelteKit                | Écosystème JS instable pour un mainteneur seul ; plus de JS côté client |
| Django + Go mélangés     | Deux langages à maintenir seul ; aucun besoin de perf à ce volume |
| Elasticsearch            | Surdimensionné pour ~1 000 annonces                        |
| Celery + Redis           | Redimensionnement synchrone suffisant à ce volume          |
| Paiement intégré         | Complexité et obligations légales hors périmètre de validation |
| Application native       | Second projet à maintenir ; PWA suffisante pour tester     |

## 8. Portes laissées ouvertes

- `Listing.payment_methods` prépare un futur paiement intégré
- Le redimensionnement est isolé dans `listings/services/images.py` : il pourra
  être déplacé vers une tâche asynchrone ou un service Go sans toucher au reste
- `accounts` prévoit un champ `phone_verified` pour une future vérification OTP
- Le statut `reserved` existe dès la V1 dans `Listing.status` pour la réservation
  acheteur → vendeur de la V2 (demande, acceptation, expiration à 7 jours)
