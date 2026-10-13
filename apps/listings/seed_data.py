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
