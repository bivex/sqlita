CREATE TABLE logs (
    previous_id INTEGER, -- Will trigger Phantom FK because missing REFERENCES
    external_api_id TEXT -- Should NOT trigger Phantom FK because type is TEXT
);

CREATE TABLE config (
    key TEXT,
    value TEXT
); -- Should NOT trigger EAV because no entity_id

CREATE TABLE translations (
    translation_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Will trigger AutoIncrement
    key TEXT,
    value TEXT
); -- Will trigger EAV because translation_id is an entity_id

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) -- Will trigger Missing Index
);

CREATE TABLE order_items (
    order_id INTEGER,
    product_id INTEGER,
    FOREIGN KEY (order_id) REFERENCES orders(id), -- Missing index
    FOREIGN KEY (product_id) REFERENCES products(id) -- Indexed below
);

CREATE INDEX idx_order_items_product ON order_items(product_id);
