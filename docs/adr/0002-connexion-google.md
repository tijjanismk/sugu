# ADR 0002 — Connexion avec Google

- Date : 2026-10-14
- Statut : accepté

## Contexte

Le propriétaire veut la connexion avec Google dès la V1 (ticket #3) : en Afrique de l'Ouest
francophone, beaucoup d'utilisateurs Android ont un compte Google, et créer un mot de passe
sur un téléphone freine l'inscription. Les comptes restent identifiés par leur email
(ADR 0001, ticket #3) ; l'inscription par numéro de téléphone (OTP SMS) reste en V2.

## Options envisagées

1. Le module « socialaccount » d'allauth, déjà la bibliothèque des comptes : fournisseur
   Google prêt, mêmes limites de débit, mêmes gabarits ; ajoute `requests`, `oauthlib` et
   `pyjwt[crypto]` (donc `cryptography`) par l'extra `django-allauth[socialaccount]`
2. Une autre bibliothèque OAuth (python-social-auth, Authlib) : un second système de comptes
   à côté d'allauth, à réconcilier à la main
3. Le bouton « Sign in with Google » en JavaScript (Google Identity Services) : script Google
   chargé sur chaque page de connexion (poids, traçage), jeton à vérifier quand même côté
   serveur
4. Ne pas le faire en V1

## Décision

Option 1. Une seule bibliothèque de comptes ; les dépendances ajoutées sont standard et
maintenues (`pyjwt` vérifie la signature du jeton d'identité de Google, `requests` échange le
code contre ce jeton). Le flux est le flux OAuth classique par redirection : aucun script
Google sur les pages de Sugu.

Réglages retenus (`config/settings/base.py`) :
- portée `openid email profile` seulement : nom et email, rien d'autre ;
- aucun jeton Google conservé (`SOCIALACCOUNT_STORE_TOKENS = False`) ;
- inscription automatique ; le nom affiché vient de Google, modifiable au profil ;
- une adresse vérifiée par Google qui correspond à un compte existant connecte ce compte
  (`SOCIALACCOUNT_EMAIL_AUTHENTICATION` et `…_AUTO_CONNECT`) : pas de doublon. Sûr parce que
  Google ne renvoie que des adresses vérifiées ; à ne pas étendre à un fournisseur qui ne
  vérifie pas les adresses ;
- connexion lancée par POST uniquement (la page GET demande confirmation) ;
- identifiants OAuth dans l'environnement (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) ; sans
  eux, le bouton n'apparaît pas.

## Conséquences

- Positives : inscription en deux touches sur Android ; pas de mot de passe à retenir.
- Négatives : quatre paquets de plus (dont `cryptography`, compilé, fourni en wheel) ; un
  compte Google Cloud à tenir (écran de consentement, adresses de retour autorisées).
- À surveiller : l'écran de consentement Google doit être publié (sinon seuls les comptes de
  test peuvent se connecter) ; adresses de retour à déclarer pour chaque domaine
  (`https://sugu.ml/comptes/google/login/callback/`, et `http://localhost:8000/…` en dev).
