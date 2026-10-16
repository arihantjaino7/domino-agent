// V2: every PROTECTS part is in the product's REQUIRES or ALLOWS_ALTERNATE. Expected: no rows.
MATCH (po:PurchaseOrder)-[pr:PROTECTS]->(o:Order)-[fp:FOR_PRODUCT]->(p:Product)
MATCH (po)-[fc:FOR_COMPONENT]->(k:Component)
OPTIONAL MATCH (p)-[r:REQUIRES|ALLOWS_ALTERNATE]->(k)
WITH po, o, p, k, count(r) AS approved
WHERE approved = 0
RETURN po.id AS po, o.id AS order_id, p.id AS product, k.id AS component
ORDER BY po, order_id
