-- Herd-Inbox: Schema Teardown (PostgreSQL)
-- For testing: drops all tables in reverse dependency order

DROP TABLE IF EXISTS audit_log      CASCADE;
DROP TABLE IF EXISTS api_keys       CASCADE;
DROP TABLE IF EXISTS subscriptions  CASCADE;
DROP TABLE IF EXISTS comments       CASCADE;
DROP TABLE IF EXISTS posts          CASCADE;
DROP TABLE IF EXISTS schema_versions CASCADE;