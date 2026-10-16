// Q-SHORTAGE-ORDERS: demand for the projection, one row per (order, required component).
// units = order qty x BOM qty.
MATCH (c:Customer)-[pc:PLACED]->(o:Order)-[fp:FOR_PRODUCT]->(p:Product)-[req:REQUIRES]->(k:Component)
MATCH (o)-[fa:FULFILLED_AT]->(pl:Plant)
WHERE o.status IN ['open', 'protected_projected'] AND o.need_day <= $horizon
RETURN o.id AS order_id, pl.id AS plant, p.id AS product, o.need_day AS need_day, o.qty AS qty,
       k.id AS component, o.qty * req.qty AS units, c.id AS customer, c.tier AS tier,
       c.penalty_per_day_cents AS penalty_cents, o.value_cents AS value_cents
ORDER BY need_day, order_id, component
