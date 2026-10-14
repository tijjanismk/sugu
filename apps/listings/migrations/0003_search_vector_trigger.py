from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations

# Configuration « french_unaccent » : le français de PostgreSQL précédé d'unaccent, pour que
# « velo » trouve « Vélo de course » (ticket #9). La recherche doit utiliser la même
# configuration (models.SEARCH_CONFIG).
CREATE_CONFIG = """
CREATE TEXT SEARCH CONFIGURATION french_unaccent (COPY = french);
ALTER TEXT SEARCH CONFIGURATION french_unaccent
    ALTER MAPPING FOR hword, hword_part, word WITH unaccent, french_stem;
"""
DROP_CONFIG = "DROP TEXT SEARCH CONFIGURATION IF EXISTS french_unaccent;"

# search_vector = titre (poids A) + description (poids B), recalculé à chaque insertion ou
# modification du titre ou de la description. Le code Python n'écrit jamais ce champ.
CREATE_TRIGGER = """
CREATE FUNCTION listings_listing_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french_unaccent'::regconfig, coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('french_unaccent'::regconfig, coalesce(NEW.description, '')), 'B');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER listings_listing_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, description ON listings_listing
    FOR EACH ROW EXECUTE FUNCTION listings_listing_search_vector_update();

UPDATE listings_listing SET title = title;
"""
DROP_TRIGGER = """
DROP TRIGGER IF EXISTS listings_listing_search_vector_trigger ON listings_listing;
DROP FUNCTION IF EXISTS listings_listing_search_vector_update();
"""


class Migration(migrations.Migration):
    """Recherche plein texte (ticket #6) : extension unaccent, configuration et trigger.

    unaccent est une extension « trusted » : elle s'installe sans superutilisateur
    (docs/security.md, l'utilisateur PostgreSQL de l'application n'est pas superutilisateur).
    """

    dependencies = [
        ("listings", "0002_listing_photo"),
    ]

    operations = [
        UnaccentExtension(),
        migrations.RunSQL(CREATE_CONFIG, DROP_CONFIG),
        migrations.RunSQL(CREATE_TRIGGER, DROP_TRIGGER),
    ]
