// Canvas: open demand, orders grouped by (customer, product, plant). Edges are aliased so every order counts.
MATCH (c:Customer)-[pc:PLACED]->(o:Order)-[fp:FOR_PRODUCT]->(p:Product)
MATCH (o)-[fa:FULFILLED_AT]->(pl:Plant)
RETURN c.id AS customer, c.name AS customer_name, c.tier AS tier, p.id AS product, pl.id AS plant,
       count(o) AS orders, collect(o.id) AS order_ids
ORDER BY customer, product, plant
