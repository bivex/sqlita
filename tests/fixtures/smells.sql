CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    ref_type TEXT,
    ref_id INTEGER,
    key TEXT,
    value TEXT,
    tags TEXT,
    user_id INTEGER
);

INSERT INTO events VALUES (1, 'post', 100, 'color', 'red', 'urgent,new', 42);

SELECT * FROM events;
