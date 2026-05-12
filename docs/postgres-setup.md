# PostgreSQL Setup

herd-inbox requires PostgreSQL 13+. SQLite is no longer supported.

## Quick setup (macOS / Homebrew)

```bash
# Install and start PostgreSQL 17
brew install postgresql@17
brew services start postgresql@17

# Create the database and user
psql postgres <<SQL
CREATE USER herd_inbox WITH PASSWORD 'changeme';
CREATE DATABASE herd_inbox OWNER herd_inbox;
GRANT ALL PRIVILEGES ON DATABASE herd_inbox TO herd_inbox;
SQL

# Set the connection URL
export DATABASE_URL="postgresql://herd_inbox:changeme@localhost:5432/herd_inbox"

# Run migrations (creates all tables)
python -m herd_inbox.db
```

## Test database

```bash
psql postgres -c "CREATE DATABASE herd_inbox_test OWNER herd_inbox;"
export TEST_DATABASE_URL="postgresql://herd_inbox:changeme@localhost:5432/herd_inbox_test"
pytest tests/ -v
```

## Using an existing PostgreSQL instance (e.g. Nova's PostgreSQL 17 on port 5432)

```bash
psql -h localhost -p 5432 -U postgres <<SQL
CREATE USER herd_inbox WITH PASSWORD 'changeme';
CREATE DATABASE herd_inbox OWNER herd_inbox;
SQL

export DATABASE_URL="postgresql://herd_inbox:changeme@localhost:5432/herd_inbox"
```

Store the password in Keychain — never in `.envrc` for production:

```bash
security add-generic-password \
  -a herd-inbox \
  -s herd-inbox-db-password \
  -w "changeme"

# Read it back in your start script:
# DB_PASS=$(security find-generic-password -a herd-inbox -s herd-inbox-db-password -w)
# export DATABASE_URL="postgresql://herd_inbox:${DB_PASS}@localhost:5432/herd_inbox"
```
