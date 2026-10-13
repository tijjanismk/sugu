# ADR 0001 — Choix du stack technique

- Date : 2026-10-10
- Statut : accepté

## Contexte

Sugu est un site de petites annonces développé et maintenu par une seule
personne assistée par l'IA. Volume visé la première année : quelques centaines
d'utilisateurs, ~1 000 annonces actives. Contraintes : connexions lentes, usage
mobile, budget d'hébergement ~20 €/mois, pas de date limite, projet destiné à
devenir une source de revenus. Profil du développeur : HTML/CSS/JS acquis,
notions de Go, base de données et Git déjà pratiqués.

## Options envisagées

1. Go + HTML serveur + htmx : le plus léger et le plus stable, mais beaucoup
   à assembler soi-même (auth, sessions, upload)
2. TypeScript + SvelteKit : un seul langage déjà connu, écosystème riche,
   mais instable dans le temps et plus de JS envoyé au client
3. Python + Django + htmx : le plus rapide vers une V1 grâce aux composants
   fournis (auth, admin, ORM, migrations, upload), nouveau langage à apprendre
4. Django avec des parties en Go : rejeté, deux langages backend pour un
   mainteneur seul sans besoin de performance avéré

## Décision

Option 3 : Django + htmx, un seul langage. Versions retenues au moment de la décision :
Python 3.14, Django 6.1 (support de Python 3.14 ; Python 3.15 n'est pas encore
supporté par Django), PostgreSQL 18, Tailwind CSS 4, htmx 2. Détail et politique
de mise à jour dans `docs/versions.md`. Raisons :

- Le projet vise à tester une idée : la vitesse de livraison de la V1 prime
- Django fournit l'authentification, l'admin (future modération) et l'upload
- HTML rendu côté serveur + htmx garantit des pages légères sur connexion lente
- Écosystème stable, adapté à une maintenance solo sur plusieurs années

Go n'est pas utilisé en V1. Il pourra être introduit plus tard pour un service
isolé (traitement d'images, temps réel) sur décision tracée dans un nouvel ADR.

## Conséquences

- Positives : V1 atteignable rapidement ; un seul langage, un seul déploiement ;
  admin Django disponible gratuitement pour la modération en V2
- Négatives : apprentissage de Python et Django ; consommation mémoire
  supérieure à Go (sans impact à ce volume) ; expérience « appli » plus
  limitée qu'avec un framework JS
- À surveiller : si le redimensionnement d'images ralentit le dépôt d'annonce,
  passer à une tâche asynchrone (ADR à écrire) ; si une appli native devient
  nécessaire, exposer une API REST depuis Django (ADR à écrire)
