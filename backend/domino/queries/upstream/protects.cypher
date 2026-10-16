// PO allocations: PROTECTS quantities are earmarked for their order in the projection.
MATCH (po:PurchaseOrder)-[pr:PROTECTS]->(o:Order)
WHERE po.status IN ['committed', 'in_transit']
RETURN po.id AS po_id, o.id AS order_id, pr.qty AS qty, o.need_day AS need_day
ORDER BY po_id, need_day, order_id
