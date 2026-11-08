CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  order_date TEXT NOT NULL,   -- YYYY-MM-DD, 주문일
  paid_date TEXT NOT NULL,    -- YYYY-MM-DD, 결제일
  status TEXT NOT NULL,       -- 'paid' | 'cancelled'
  total_excl_tax REAL NOT NULL,
  total_incl_tax REAL NOT NULL
);
CREATE TABLE refunds (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id),
  refund_date TEXT NOT NULL,
  amount_excl_tax REAL NOT NULL,
  amount_incl_tax REAL NOT NULL
);
INSERT INTO customers VALUES (1,'Alpha'),(2,'Bravo'),(3,'Charlie'),(4,'Delta'),(5,'Echo'),(6,'Foxtrot'),(7,'Golf'),(8,'Hotel');
INSERT INTO orders VALUES
 (1, 1, '2026-10-03', '2026-10-04', 'paid', 230, 253.0),
 (2, 1, '2026-10-21', '2026-10-22', 'paid', 110, 121.0),
 (3, 2, '2026-10-11', '2026-10-12', 'paid', 320, 320.0),
 (4, 2, '2026-10-25', '2026-10-25', 'cancelled', 150, 165.0),
 (5, 3, '2026-10-15', '2026-11-02', 'paid', 300, 330.0),
 (6, 3, '2026-10-02', '2026-10-03', 'paid', 40, 44.0),
 (7, 4, '2026-10-09', '2026-10-10', 'paid', 280, 336.0),
 (8, 4, '2026-09-29', '2026-10-01', 'paid', 90, 108.0),
 (9, 5, '2026-10-30', '2026-10-31', 'paid', 260, 286.0),
 (10, 5, '2026-10-05', '2026-10-06', 'paid', 60, 66.0),
 (11, 6, '2026-10-17', '2026-10-18', 'cancelled', 400, 440.0),
 (12, 6, '2026-10-12', '2026-10-13', 'paid', 120, 132.0),
 (13, 7, '2026-09-14', '2026-09-15', 'paid', 1000, 1100.0),
 (14, 8, '2026-11-02', '2026-11-03', 'paid', 500, 550.0),
 (15, 7, '2026-10-26', '2026-10-27', 'paid', 75, 86.25);
INSERT INTO refunds VALUES
 (1, 3, '2026-10-20', 90, 90),
 (2, 10, '2026-10-07', 60, 66);
