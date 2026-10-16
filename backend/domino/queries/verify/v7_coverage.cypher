// V7: orders marked protected (projected) have PROTECTS quantity covering their need for that part.
// Expected: no rows.
MATCH (po:PurchaseOrder)-[pr:PROTECTS]->(o:Order {status: 'protected_projected'})-[fp:FOR_PRODUCT]->(p:Product)
MATCH (po)-[fc:FOR_COMPONENT]->(k:Component)
WITH o, p, k, sum(pr.qty) AS covered
OPTIONAL MATCH (p)-[req:REQUIRES]->(k)
OPTIONAL MATCH (p)-[alt:ALLOWS_ALTERNATE]->(k)
WITH o, k, covered, o.qty * coalesce(req.qty, alt.qty, 0) AS needed
WHERE covered < needed
RETURN o.id AS order_id, k.id AS component, covered, needed
ORDER BY order_id
