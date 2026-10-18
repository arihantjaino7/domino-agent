// Delivered purchase orders and how they went (Shipments view, get_delivery_outcomes), with the orders each
// one protected and their final status.
MATCH (po:PurchaseOrder)-[fs:FROM_SITE]->(s:Site)
WHERE po.status IN ['received', 'delayed']
MATCH (po)-[fc:FOR_COMPONENT]->(k:Component)
MATCH (po)-[dt:DELIVERS_TO]->(pl:Plant)
OPTIONAL MATCH (po)-[pr:PROTECTS]->(o:Order)
RETURN po.id AS po_id, s.id AS site, s.name AS site_name, k.id AS component, pl.id AS plant, po.mode AS mode,
       po.qty AS qty, po.status AS status, po.first_arrival_day AS planned_day, po.arrived_day AS arrived_day,
       po.days_late AS days_late, po.received_day AS received_day,
       collect({order_id: o.id, qty: pr.qty, need_day: o.need_day, status: o.status, delivered_day: o.delivered_day,
                late_days: o.late_days}) AS orders
ORDER BY po_id
