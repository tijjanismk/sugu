# Rituels de travail avec l'IA — Sugu

## Démarrer une session

**Avec Claude Code** (ouvert à la racine du dépôt) : `CLAUDE.md` et donc `CONTEXT.md`
sont chargés automatiquement. Il suffit de dire : « Ticket #N. Lis-le dans
`docs/tickets.md` et propose un plan avant de coder. » Utilise le mode plan pour
valider l'approche avant qu'il écrive quoi que ce soit.

**Dans un chat classique**, fournir dans l'ordre :

1. `CONTEXT.md`
2. Le ticket en cours (copie de l'issue)
3. Les fichiers directement concernés (modèles, vues, tests existants de l'app)
4. `docs/design.md` seulement si le ticket touche à l'architecture

Puis : « Propose un plan en 5 points maximum avant d'écrire du code. »
Valider ou corriger le plan, ensuite seulement laisser l'IA coder.

## Terminer une session

Mettre à jour la section « État d'avancement » de `CONTEXT.md` (dernière tâche
terminée, tâche en cours, points ouverts). C'est ce qui permet à la session
suivante de reprendre sans perte.

## Quand ouvrir une nouvelle conversation pour une revue critique

Une conversation qui a écrit le code est mauvaise pour le juger : elle défend
ses choix. Ouvrir une conversation vierge :

- avant de fusionner chaque PR (revue de code)
- après les tickets qui touchent au modèle de données (#3, #6, #12)
- en cas de blocage depuis plus d'une heure
- avant d'écrire un ADR
- tous les cinq tickets environ, pour une critique d'architecture globale

## Prompt de revue de code

```
Tu es un relecteur de code senior, exigeant mais constructif. Tu relis une pull
request d'un projet Django. Tu n'as pas écrit ce code et tu ne dois pas être
complaisant.

Contexte du projet : [coller CONTEXT.md]
Règles de sécurité : [coller docs/security.md, section Règles]
Ticket : [coller l'issue]
Diff de la PR : [coller le diff, ou les fichiers modifiés]

Analyse dans cet ordre, en français :
1. Bugs et cas limites non gérés (avec un exemple concret pour chacun)
2. Failles de sécurité : pour chaque vue, qui a le droit ? un autre utilisateur
   peut-il atteindre cette donnée en changeant un identifiant ? injection,
   données exposées, CSRF, fichier non validé
3. Problèmes de performance (requêtes N+1, index manquants, images)
4. Écarts par rapport aux conventions de CONTEXT.md
5. Tests : qu'est-ce qui n'est pas couvert et devrait l'être ?
6. Lisibilité et simplicité : qu'est-ce qui pourrait être supprimé ?

Classe chaque remarque en BLOQUANT / IMPORTANT / MINEUR. Termine par un verdict :
« à fusionner », « à corriger avant fusion » ou « à reprendre ». Ne propose pas
de réécrire le code sauf si je te le demande.
```

## Prompt de critique d'architecture

```
Tu es un architecte logiciel senior. Tu dois trouver les faiblesses de cette
architecture, pas la valider. Le projet est maintenu par une seule personne.

Document de conception : [coller docs/design.md]
Schéma de données : [coller docs/database.md]
ADR existants : [coller les titres et décisions]
État actuel : [coller la section État d'avancement de CONTEXT.md]

Réponds en français :
1. Quelles décisions vont poser problème dans 6 mois, et pourquoi ?
2. Quelle est la partie la plus fragile du système ? Comment la casser ?
3. Qu'est-ce qui est surdimensionné pour le volume visé ?
4. Qu'est-ce qui manque pour la monétisation future (mises en avant payantes,
   modération) ?
5. Si tu ne devais changer qu'une seule chose, laquelle ?

Sois précis : chaque critique doit citer un élément concret du document. Ne
propose pas de changer de stack.
```

## Quand écrire un nouvel ADR

- Ajout d'une dépendance qui n'est pas dans `CONTEXT.md`
- Changement d'un élément du stack listé dans `CONTEXT.md` (y compris ajouter Go)
- Modification du modèle de données qui touche des données existantes
- Décision de sécurité ou de données personnelles
- Hésitation de plus de trente minutes entre deux approches : la décision
  mérite d'être écrite, même si elle paraît petite
- Retour sur un ADR précédent (statut « remplacé par »)

Un ADR fait une page maximum. Il ne décrit pas *comment* c'est codé, mais
*pourquoi* ce choix. Modèle : `docs/adr/template.md`.
