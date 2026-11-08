CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  order_date TEXT NOT NULL,           -- YYYY-MM-DD
  status TEXT NOT NULL,               -- 'paid' | 'cancelled'
  total_excl_tax REAL NOT NULL,
  total_incl_tax REAL NOT NULL
);
INSERT INTO customers VALUES (1,'Alpha'),(2,'Bravo'),(3,'Charlie'),(4,'Delta'),(5,'Echo');
INSERT INTO orders VALUES
 (1,1,'2026-10-03','paid',100,110),
 (2,1,'2026-10-20','paid',100,110),
 (3,2,'2026-10-11','paid',190,190),
 (4,2,'2026-10-25','cancelled',100,110),
 (5,3,'2026-10-15','paid',180,198),
 (6,4,'2026-10-09','paid',170,204),
 (7,5,'2026-10-30','paid',50,55),
 (8,5,'2026-09-14','paid',1000,1100),
 (9,4,'2026-11-02','paid',500,600),
 (10,3,'2026-09-28','paid',300,330);
