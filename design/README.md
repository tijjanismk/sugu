Sugu est le marché du quartier dans la poche : des particuliers qui vendent et achètent près de chez eux, sur des téléphones d'entrée de gamme et des connexions lentes. L'interface est chaleureuse par ses matières (papier, indigo, ocre) et ses coins arrondis, jamais par de la décoration. Tout ce qui suit est une règle pour qui construit un écran Sugu.

## Principes

1. **Le prix d'abord.** Sur une carte annonce, l'œil tombe sur le prix avant le titre : style `price`, couleur `indigo`, chiffres tabulaires.
2. **Un pouce.** Toute action principale se fait d'une main : barre de navigation en bas, bouton de validation collé au bas de l'écran, zones tactiles de `touch-min` (44 px) minimum.
3. **Léger par construction.** Pas d'ombre sur les cartes (un filet `line` suffit), pas de dégradé, pas d'image décorative, photos en WebP aux dimensions réservées, squelettes plutôt que spinners.
4. **Une seule couleur chaude par écran.** `sun` est réservé à l'action « Déposer une annonce ». Tout le reste s'appuie sur `indigo`, `ink` et les surfaces.
5. **Mots simples.** Une phrase courte, un verbe actif, le même mot du bouton au message de confirmation.

## Contenu

- Vouvoyez (« Votre annonce est publiée »), ton chaleureux, phrases courtes. Pas de jargon : « Déposer une annonce », pas « Créer un listing ».
- Casse de phrase partout, y compris dans les boutons et les libellés : « Voir plus », pas « VOIR PLUS ».
- Un bouton dit ce qu'il fait et son résultat garde le même mot : « Publier » → « Annonce publiée ». Jamais « Valider », « OK », « Soumettre ».
- Prix : espace insécable comme séparateur de milliers, unité après, jamais de décimales : « 45 000 FCFA ». Prix absent : « À débattre » en style `price`, couleur `ink-muted`.
- Dates relatives jusqu'à sept jours (« il y a 2 h », « hier », « il y a 3 j »), puis la date courte (« 12 oct. »).
- Lieu : quartier puis ville, séparés d'une virgule : « Hamdallaye, Bamako ». Hors de la ville : « À 20 km de Ségou », ou « Moribabougou, à 20 km de Bamako ».
- Erreurs : dire ce qui bloque et comment débloquer, en une phrase, sans s'excuser : « Ajoutez au moins une photo pour publier. » Pas de « Oups ».
- Écran vide : une invitation à agir, pas un constat : « Aucun favori pour l'instant. Touchez le cœur d'une annonce pour la retrouver ici. »
- Pas d'émoji dans l'interface. Les messages entre utilisateurs en contiennent s'ils le veulent.

## Couleurs

- Page : `surface`. Cartes, feuilles, barres : `surface-raised`, bordées de `line`. Creux (champ de recherche au repos, placeholders, squelettes) : `surface-sunken`.
- Texte : `ink` ; secondaire (ville, date, aide) : `ink-muted`. Les deux tiennent 5:1 et plus sur les trois surfaces, dans les deux thèmes.
- `indigo` est la marque : bouton principal (texte `on-indigo`), prix, liens, onglet et icône actifs. `indigo-soft` derrière un texte ou une icône `indigo` (tuile de catégorie, avatar, badge « Nouveau »).
- `sun` : un seul usage, l'action « Déposer une annonce » (bouton de la barre basse, bouton d'accueil), texte `on-sun`. Jamais en texte ni en filet. `sun-soft` pour le badge « Mobile money » avec texte `ink`.
- États : `success` / `success-soft`, `danger` / `danger-soft`. Toujours accompagnés d'un mot ou d'une icône : la couleur n'est jamais le seul signal.
- `heart` uniquement pour le cœur actif des favoris.
- Bords de contrôle (champs, chips, boutons secondaires) : `line-strong`, qui tient 3:1 ; `line` est décoratif.
- Focus clavier : anneau plein de 3 px en `focus`, décalé de 2 px.
- Les deux thèmes sont servis par `tokens.css` sur `data-theme` ; suivez le réglage du téléphone avec `prefers-color-scheme`, et proposez le choix manuel dans le profil. Aucune couleur n'est écrite en dur : en thème sombre l'indigo s'éclaircit et `on-indigo` devient sombre.

## Typographie

- Une seule famille : Figtree (`--font-sans`), en police variable, sous-ensemble latin, chargée avec `font-display: swap` ; le texte s'affiche d'abord dans la police du téléphone. Aucune seconde police web.
- Titres : `display` (accueil), `title` (titre de page), `heading` (section, titre d'annonce). Texte : `body`, `body-strong`, `small`, `small-strong`, `caption`. Prix : `price` (carte), `price-lg` (page de l'annonce).
- Les champs de saisie sont en `body` (16 px) : en dessous, les téléphones zooment au focus.
- Alignez tout à gauche. Centré uniquement pour les états vides et les écrans de confirmation.
- Jamais de capitales pour un libellé, jamais un seul mot coloré dans un titre.

## Espacements, rayons, dimensions

- Marge latérale d'un écran : `space-4`. Entre sections : `space-6`. Intérieur d'une carte annonce : `space-3`. Grille d'annonces : gouttière `space-3`, deux colonnes sur mobile, trois à partir de 640 px, quatre à partir de 1024 px dans `page-max`.
- Rayons : `radius-sm` badges et squelettes, `radius-md` boutons, champs et tuiles photo, `radius-lg` cartes, bulles et tuiles de catégorie, `radius-full` chips, recherche, avatars, bouton favori et bouton Déposer.
- Hauteurs : `touch-min` pour tout élément tactile, `touch-lg` pour le bouton de validation d'un formulaire et l'appel du vendeur. Formulaires et pages de lecture tiennent dans `content-max`.

## Mise en page

- Mobile d'abord, une colonne. La barre de navigation basse (Accueil, Recherche, Déposer, Favoris, Messages) est présente sur toutes les pages de premier niveau et disparaît dans les flux (dépôt d'annonce, conversation ouverte), remplacée par l'action du flux collée en bas.
- Barre du haut : nom « Sugu » en `indigo` sur l'accueil ; flèche retour, titre `title` et une action au plus sur les autres pages.
- À partir de 1024 px, la barre basse devient une barre haute avec « Déposer une annonce » en `sun` à droite ; la grille passe à quatre colonnes.
- Un seul élément « flottant » par écran, et il porte `shadow-float` : la barre basse ou une feuille. Rien d'autre n'a d'ombre.

## Iconographie

- Lucide, en SVG inliné dans les gabarits Django, 22 px dans les contrôles, 24 px dans la barre de navigation, trait de 2 px, bouts et jointures arrondis, `currentColor`. Pas de police d'icônes, pas d'émoji.
- Une icône accompagne un mot sauf dans la barre de navigation et le bouton favori, où le sens est appris ; ces deux-là portent un `aria-label`.
- Catégories : une icône par catégorie sur `indigo-soft`, en `indigo`.

## Images

- Photos d'annonce : WebP, 1200 px pour la page, 400 px pour la carte, ratio 4:3, `width` et `height` renseignés pour réserver la place ; `loading="lazy"` au-delà des quatre premières cartes.
- Sans photo : un aplat `surface-sunken` avec l'icône appareil photo en `ink-muted`. Jamais une image générique.
- La photo d'index 0 est la couverture ; le dépôt le dit à l'utilisateur sur la tuile.
- Bannières de l'accueil (`sg-banner`) : WebP 1200 et 600 px, ratio 2:1, contenues jamais recadrées, rayon `radius-lg` sur `surface-sunken` ; défilement au doigt avec la suivante qui dépasse, sans défilement automatique ; seule la première chargée tout de suite.

## Formulaires

- Choix unique (motif d'un signalement) : boutons radio `sg-check`, comme les cases à cocher, une option par ligne de 44 px.
- Icône `flag` (Lucide) pour « Signaler cette annonce », en bouton discret `sg-btn--quiet`.

## Mouvement

- Aucune animation d'entrée. Les seuls mouvements répondent à un geste : le cœur qui se remplit, une feuille qui monte, un bouton qui s'enfonce de 1 px.
- Chargement : squelette `surface-sunken` qui pulse doucement ; immobile sous `prefers-reduced-motion`.
- Transitions de 150 ms au plus.

## États et accessibilité

- Tout contrôle a un état focus visible (`focus`), un état désactivé à 50 % d'opacité avec curseur interdit, et, pour une action réseau, un état en cours avec spinner et libellé (« Publication… ») — jamais un bouton muet.
- Les images ont un `alt` (le titre de l'annonce), les boutons icône un `aria-label`, les onglets `aria-current="page"`, les chips `aria-pressed`.
- Contraste : texte 4,5:1 minimum, grands textes et contrôles 3:1, dans les deux thèmes ; le tableau des tokens tient ces seuils, les composants aussi.
