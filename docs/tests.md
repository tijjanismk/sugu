# Stratégie de tests — Sugu

## Tests unitaires — `pytest` + `pytest-django` + `factory-boy`

Ce qu'on teste : la logique métier dans `services.py` et les règles des modèles.

- Redimensionnement : une image 3000×2000 produit une version 1200 px et une
  miniature 400 px en WebP, avec les bonnes dimensions enregistrées
- Validation d'annonce : prix négatif refusé, plus de 6 photos refusé, titre
  trop long refusé
- Construction de la requête de recherche : les filtres combinés donnent la
  bonne requête ORM
- Contraintes : une seule conversation par couple (annonce, acheteur), un seul
  favori par couple (utilisateur, annonce)
- Transitions de statut : `published → sold` autorisé, `sold → published` refusé

Les tests unitaires n'appellent ni R2, ni le réseau : le stockage est
`FileSystemStorage` vers un dossier temporaire en `settings/test.py`.

## Tests d'intégration — `pytest-django` avec le client de test Django

Ce qu'on teste : les vues avec la base de données réelle (PostgreSQL en CI, pas
SQLite, pour que la recherche plein texte soit testée).

- Permissions : seul le propriétaire peut modifier ou supprimer son annonce ;
  un vendeur ne peut pas s'écrire à lui-même ; les non-connectés sont redirigés
- Rendu htmx : avec l'en-tête `HX-Request`, la vue renvoie le partial ; sans,
  la page complète
- Recherche : « vélo » trouve « Vélo de course », filtre par ville et fourchette
  de prix
- Messagerie : envoyer un message crée la conversation si elle n'existe pas,
  incrémente le compteur de non-lus du destinataire
- Dépôt d'annonce complet via POST multipart avec une vraie image

## Tests de bout en bout — Playwright (Python)

Trois parcours seulement, les plus critiques pour « tester l'idée » :

1. Inscription → dépôt d'une annonce avec photo → l'annonce apparaît en recherche
2. Un acheteur contacte un vendeur → le vendeur voit le message et répond
3. Ajout et retrait d'un favori depuis la liste

Ils tournent contre un serveur local avec les données de `seed`. En CI,
uniquement sur `main` (trop lents pour chaque push).

## Ce qu'il n'est PAS utile de tester

- Le fonctionnement interne de Django, allauth ou l'admin
- Le HTML exact ou les classes Tailwind : on teste la présence de contenu et
  les codes HTTP, pas la mise en page
- Le service worker en V1
- La connexion réelle à R2 : un seul test manuel après le premier déploiement
- Les getters triviaux et les `__str__`

## Commandes

```bash
uv run pytest                          # unitaires + intégration
uv run pytest --cov=apps               # avec couverture
uv run pytest tests/e2e --base-url http://localhost:8000   # bout en bout
```

## Organisation

- `apps/<app>/tests/test_models.py`, `test_services.py`, `test_views.py`
- `apps/<app>/tests/factories.py` pour factory-boy
- `tests/e2e/test_<parcours>.py` pour Playwright
