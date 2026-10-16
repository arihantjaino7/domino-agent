// V4: every PROTECTS arrives by the order's need day. Expected: no rows.
MATCH (po:PurchaseOrder)-[pr:PROTECTS]->(o:Order)
WHERE pr.arrival_day > o.need_day
RETURN po.id AS po, o.id AS order_id, pr.arrival_day AS arrival_day, o.need_day AS need_day
ORDER BY po, order_id
