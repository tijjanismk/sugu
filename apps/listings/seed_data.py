"""Données de référence chargées par `manage.py seed`. Le slug est la clé : ne pas le changer
une fois en production (les URL de recherche s'en servent)."""

# (nom, slug, icône Lucide, [(nom, slug), …]) — l'ordre de la liste est l'ordre d'affichage.
CATEGORIES = [
    ("Téléphones", "telephones", "smartphone", [
        ("Smartphones", "smartphones"),
        ("Accessoires", "accessoires-telephones"),
    ]),
    ("Véhicules", "vehicules", "car", [
        ("Voitures", "voitures"),
        ("Pièces auto", "pieces-auto"),
    ]),
    ("Immobilier", "immobilier", "house", [
        ("Locations", "locations"),
        ("Ventes", "ventes-immobilier"),
    ]),
    ("Mode", "mode", "shirt", [
        ("Vêtements", "vetements"),
        ("Chaussures", "chaussures"),
    ]),
    ("Maison", "maison", "armchair", [
        ("Meubles", "meubles"),
        ("Électroménager", "electromenager"),
    ]),
    ("Outils", "outils", "wrench", [
        ("Bricolage", "bricolage"),
        ("Matériel agricole", "materiel-agricole"),
    ]),
    ("Vélos et motos", "velos-motos", "bike", [
        ("Motos", "motos"),
        ("Vélos", "velos"),
    ]),
    ("Informatique", "informatique", "laptop", [
        ("Ordinateurs", "ordinateurs"),
        ("TV et audio", "tv-audio"),
    ]),
    ("Emploi et services", "emploi-services", "briefcase", [
        ("Offres d'emploi", "offres-emploi"),
        ("Services", "services"),
    ]),
    ("Loisirs", "loisirs", "ball", [
        ("Sport", "sport"),
        ("Livres et musique", "livres-musique"),
    ]),
]  # fmt: skip

# (nom, slug, région) — principales villes du Mali, régions selon le découpage de 2023.
CITIES = [
    ("Bamako", "bamako", "District de Bamako"),
    ("Sikasso", "sikasso", "Sikasso"),
    ("Ségou", "segou", "Ségou"),
    ("Kayes", "kayes", "Kayes"),
    ("Mopti", "mopti", "Mopti"),
    ("Koutiala", "koutiala", "Koutiala"),
    ("Kati", "kati", "Koulikoro"),
    ("San", "san", "San"),
    ("Gao", "gao", "Gao"),
    ("Tombouctou", "tombouctou", "Tombouctou"),
]

# Vendeur des annonces de démonstration : compte sans mot de passe utilisable.
DEMO_SELLER = {"email": "demo@sugu.ml", "display_name": "Boutique démo"}

_CASH = "cash_on_delivery"
_MOMO = "mobile_money"

# Annonces de démonstration (sans photo : les photos arrivent avec le dépôt, ticket #7).
# `previous_price` : baisse de prix récente, pour voir le badge (ticket #8).
DEMO_LISTINGS = [
    {
        "title": "Vélo de course Peugeot, pneus neufs",
        "category": "velos",
        "city": "bamako",
        "price": 45000,
        "previous_price": 55000,
        "payment_methods": [_CASH, _MOMO],
        "description": "Cadre aluminium, 21 vitesses, pneus changés le mois dernier. "
        "Idéal pour aller au travail. À voir à Hamdallaye.",
    },
    {
        "title": "Samsung Galaxy A15, 128 Go",
        "category": "smartphones",
        "city": "bamako",
        "price": 85000,
        "payment_methods": [_MOMO],
        "description": "Acheté il y a six mois, écran sans rayure, avec chargeur et coque.",
    },
    {
        "title": "Moto Jakarta 125, bon état",
        "category": "motos",
        "city": "segou",
        "price": 350000,
        "payment_methods": [_CASH],
        "description": "Papiers à jour, entretien régulier, démarre au quart de tour.",
    },
    {
        "title": "Toyota Corolla 2012",
        "category": "voitures",
        "city": "bamako",
        "price": 4500000,
        "previous_price": 4800000,
        "payment_methods": [_CASH],
        "description": "Boîte manuelle, climatisation, 180 000 km. Visite possible le week-end.",
    },
    {
        "title": "Appartement F3 à louer, Kalaban Coura",
        "category": "locations",
        "city": "bamako",
        "price": 150000,
        "payment_methods": [_CASH, _MOMO],
        "description": "Deux chambres, salon, cuisine, eau et électricité. Loyer mensuel.",
    },
    {
        "title": "Terrain de 300 m² titré",
        "category": "ventes-immobilier",
        "city": "kati",
        "price": None,
        "payment_methods": [_CASH],
        "description": "Terrain titré, quartier calme, proche de la route goudronnée. "
        "Prix à débattre.",
    },
    {
        "title": "Boubou bazin brodé, taille L",
        "category": "vetements",
        "city": "sikasso",
        "price": 25000,
        "payment_methods": [_MOMO],
        "description": "Bazin riche, broderie faite main, porté une seule fois.",
    },
    {
        "title": "Canapé trois places",
        "category": "meubles",
        "city": "bamako",
        "price": 120000,
        "payment_methods": [_CASH],
        "description": "Tissu gris, très bon état, à récupérer sur place.",
    },
    {
        "title": "Réfrigérateur Haier 200 L",
        "category": "electromenager",
        "city": "mopti",
        "price": 140000,
        "payment_methods": [_CASH, _MOMO],
        "description": "Fonctionne parfaitement, garantie terminée, "
        "vendu pour cause de déménagement.",
    },
    {
        "title": "Ordinateur portable HP 15 pouces",
        "category": "ordinateurs",
        "city": "bamako",
        "price": 175000,
        "payment_methods": [_MOMO],
        "description": "Core i5, 8 Go de mémoire, disque SSD 256 Go, batterie neuve.",
    },
    {
        "title": "Motopompe pour arrosage",
        "category": "materiel-agricole",
        "city": "koutiala",
        "price": 95000,
        "payment_methods": [_CASH],
        "description": "Moteur 6,5 ch, tuyaux fournis, idéale pour le maraîchage.",
    },
    {
        "title": "Cours de soutien en mathématiques",
        "category": "services",
        "city": "kayes",
        "price": 10000,
        "payment_methods": [_CASH, _MOMO],
        "description": "Collège et lycée, à domicile, deux séances par semaine. Prix mensuel.",
    },
]
