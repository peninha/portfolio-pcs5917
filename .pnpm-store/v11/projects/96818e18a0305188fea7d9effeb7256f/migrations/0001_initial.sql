CREATE TABLE IF NOT EXISTS commits (
  revision INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS state_chunks (
  part INTEGER PRIMARY KEY,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
  hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('session', 'invite')),
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS tokens_expiry ON tokens(expires_at);
CREATE TABLE IF NOT EXISTS auth_limits (
  bucket TEXT PRIMARY KEY,
  count INTEGER NOT NULL
);
