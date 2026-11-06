-- Creates the application role. It is NOT a superuser and cannot bypass row level
-- security, so the database itself enforces workspace isolation (DEC-012).
-- Use the same statements in the Supabase SQL editor (with your own password).
CREATE ROLE daleel_app LOGIN PASSWORD 'daleel_local_dev' NOSUPERUSER NOBYPASSRLS NOCREATEROLE;
GRANT CREATE, USAGE ON SCHEMA public TO daleel_app;
ALTER DATABASE daleel OWNER TO daleel_app;
