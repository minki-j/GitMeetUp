SELECT column_name
FROM information_schema.columns
WHERE table_name = %(table_name)s