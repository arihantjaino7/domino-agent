// Committed purchase orders (not yet received) with their source, part and destination.
MATCH (po:PurchaseOrder)-[fs:FROM_SITE]->(s:Site)
MATCH (po)-[fc:FOR_COMPONENT]->(k:Component)
MATCH (po)-[dt:DELIVERS_TO]->(pl:Plant)
WHERE po.status IN ['committed', 'in_transit']
RETURN po.id AS po_id, s.id AS site, k.id AS component, pl.id AS plant, po.rate_wk AS rate_wk, po.qty AS qty,
       po.first_arrival_day AS first_arrival_day, po.unit_price_cents AS unit_price_cents
ORDER BY po_id
