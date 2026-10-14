from django.db import migrations

# Ticket #9 : le quartier entre dans la recherche (« sabalibougou » trouve l'annonce).
# Poids : titre A, quartier B, description C ; la pertinence classe d'abord le titre.
UPDATE_TRIGGER = """
CREATE OR REPLACE FUNCTION listings_listing_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french_unaccent'::regconfig, coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('french_unaccent'::regconfig, coalesce(NEW.neighborhood, '')), 'B') ||
        setweight(to_tsvector('french_unaccent'::regconfig, coalesce(NEW.description, '')), 'C');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS listings_listing_search_vector_trigger ON listings_listing;
CREATE TRIGGER listings_listing_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, description, neighborhood ON listings_listing
    FOR EACH ROW EXECUTE FUNCTION listings_listing_search_vector_update();

UPDATE listings_listing SET title = title;
"""

# Retour à la version de la migration 0003 (titre A, description B).
RESTORE_TRIGGER = """
CREATE OR REPLACE FUNCTION listings_listing_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french_unaccent'::regconfig, coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('french_unaccent'::regconfig, coalesce(NEW.description, '')), 'B');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS listings_listing_search_vector_trigger ON listings_listing;
CREATE TRIGGER listings_listing_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, description ON listings_listing
    FOR EACH ROW EXECUTE FUNCTION listings_listing_search_vector_update();

UPDATE listings_listing SET title = title;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0004_listing_place"),
    ]

    operations = [
        migrations.RunSQL(UPDATE_TRIGGER, RESTORE_TRIGGER),
    ]
