.open --readonly client.db
SELECT "This database is version " || version FROM version;