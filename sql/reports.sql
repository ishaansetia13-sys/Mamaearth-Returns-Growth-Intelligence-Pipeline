-- Reports use all 180 original orders, including the five duplicates.
-- (a) Output: total_orders=180, total_revenue=99860.20, avg_order_value=554.78
-- (a) Order totals
SELECT COUNT(*) AS total_orders,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_revenue,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS avg_order_value
FROM orders o JOIN products p ON o.product_id = p.product_id;

-- (b) Output: total_orders=180, rated_orders=165, unrated_orders=15
-- (b) COUNT(*) includes unrated orders; COUNT(rating) excludes NULL.
SELECT COUNT(*) AS total_orders, COUNT(rating) AS rated_orders,
       COUNT(*) - COUNT(rating) AS unrated_orders FROM orders;

-- (c1) Output: C045 | Vihaan
-- (c1) LEFT JOIN keeps customers even when no matching order exists.
SELECT c.customer_id, c.name FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name HAVING COUNT(o.order_id) = 0;

-- (c2) Output: C045 | Vihaan
-- (c2) Independent check of customers without orders.
SELECT customer_id, name FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);

-- (d) Output: Jaipur | 19 | 8 | 42.1; Lucknow | 49 | 15 | 30.6; Bangalore | 33 | 8 | 24.2
-- (d) City-level return rates over original orders.
SELECT c.city, COUNT(*) AS total_orders, SUM(o.returned) AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 1) AS return_rate_pct
FROM orders o JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.city HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;

-- (e1) Output: C043 Reyansh 12920.00; C026 Isha 8371.60; C008 Meera 4564.60; C011 Arjun 4111.00; C042 Sanya 3785.00
-- (e1) Customer spend. customer_id ASC makes tied spend rankings reproducible.
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o JOIN products p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name ORDER BY total_spend DESC, c.customer_id ASC LIMIT 5;

-- (e2) Output: C008 Meera 4564.60; C011 Arjun 4111.00; C042 Sanya 3785.00
-- (e2) Positions 3–5 without calculating the first five separately.
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o JOIN products p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name ORDER BY total_spend DESC, c.customer_id ASC LIMIT 3 OFFSET 2;

-- (f) Output: Haircare 54 44956.10; Skincare 60 27346.00; Babycare 30 16805.00; PersonalCare 36 10753.10
-- (f) Three-table join and category-level revenue.
SELECT p.category, COUNT(*) AS order_count,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS category_revenue
FROM orders o JOIN products p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY p.category ORDER BY category_revenue DESC;

-- (g) Output: C001 Aarav; C003 Aditi; C004 Ananya; C011 Arjun; C021 Aryan; C030 Anika; C031 Aditya; C036 Aisha; C041 Ayaan; C044 Aria
-- (g) Customer names beginning with A.
SELECT customer_id, name FROM customers WHERE name LIKE 'A%' ORDER BY customer_id;

-- (h) Output: Ad; Organic; Referral; Social
-- (h) Unique acquisition channels.
SELECT DISTINCT acquisition_source FROM customers ORDER BY acquisition_source;

-- (i) Output: Gold 28; Silver 17
-- (i) Run once after reports (a)–(h), on a fresh database.
ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);
UPDATE customers SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold' ELSE 'Silver' END;
SELECT loyalty_tier, COUNT(*) AS customer_count FROM customers GROUP BY loyalty_tier ORDER BY loyalty_tier;
