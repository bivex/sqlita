CREATE TABLE users (
    email TEXT, -- Missing NOT NULL
    created_at TEXT -- Missing CHECK constraint and NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER, -- Not primary key, missing NOT NULL
    status TEXT -- Missing NOT NULL
);
