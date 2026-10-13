# Workflow Git — Sugu

## Branches

- `main` : toujours déployable, protégée (CI verte obligatoire, pas de push direct)
- Une branche par ticket, préfixée du numéro d'issue GitHub :
  - `feat/12-recherche-plein-texte`
  - `fix/31-upload-photo-heic`
  - `docs/adr-0002`
  - `chore/deps`

## Commits (Conventional Commits, en français)

```
feat(listings): ajoute la recherche plein texte avec filtres
fix(messaging): empêche un vendeur de s'écrire à lui-même
test(listings): couvre le redimensionnement WebP
docs(adr): ADR 0002 inscription par téléphone
chore(ci): ajoute le job e2e sur main
refactor(accounts): déplace la logique de profil dans services.py
```

Préfixes : `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `style`.
Le scope est le nom de l'app ou du domaine concerné.

## Pull request en solo

Chaque ticket passe par une PR, même seul, parce que c'est le moment de la revue.

1. Créer l'issue GitHub à partir du ticket (`docs/tickets.md`)
2. Brancher, développer, commiter souvent
3. Ouvrir la PR avec le modèle `.github/pull_request_template.md`
4. Attendre la CI verte
5. **Revue par l'IA dans une nouvelle conversation** (prompt dans
   `docs/ia-rituels.md`), corriger
6. Relire soi-même le diff une dernière fois sur GitHub
7. *Squash and merge*, supprimer la branche
8. Taguer `v0.x.0` à chaque jalon fonctionnel, `v1.0.0` au minimum viable

## Versions

- `v0.1.0` : première mise en production (ticket #15)
- `v1.0.0` : minimum viable complet (ticket #17)
- Ensuite : SemVer, un tag par déploiement en production
