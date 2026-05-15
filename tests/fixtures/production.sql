PRAGMA journal_mode = WAL;
-- Missing PRAGMA synchronous = NORMAL (SuboptimalSynchronous)
-- Missing PRAGMA foreign_keys = ON (PhantomForeignKey)

CREATE TABLE users (
    id INTEGER, -- Missing PRIMARY KEY (MissingPrimaryKey)
    email TEXT, -- Missing COLLATE NOCASE (CaseSensitiveLookup) and NOT NULL (NotNullCoverage)
    password TEXT, -- (PlaintextSecrets)
    created_at TEXT -- (DateAsText) and NOT NULL (NotNullCoverage)
); -- Missing STRICT (NonStrictMode)

CREATE TABLE profile (
    user_id INTEGER PRIMARY KEY,
    bio TEXT
) STRICT; -- Has STRICT, but maybe missing other things
