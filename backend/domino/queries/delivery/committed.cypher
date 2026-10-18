// Committed purchase orders waiting for delivery, with what the outcome model needs: the source edge's
// approved spare and how much of it is now reserved, and the reliability of the company that runs the site.
MATCH (d:Decision)-[cr:CREATED]->(po:PurchaseOrder)-[fs:FROM_SITE]->(s:Site)
MATCH (po)-[fc:FOR_COMPONENT]->(k:Component)
MATCH (po)-[dt:DELIVERS_TO]->(pl:Plant)
WHERE po.status = 'committed'
MATCH (s)-[cs:CAN_SUPPLY]->(pl)
WHERE cs.component_id = k.id
OPTIONAL MATCH (sup:Supplier)-[op:OPERATES]->(s)
RETURN po.id AS po_id, d.id AS decision_id, s.id AS site, s.name AS site_name, sup.id AS supplier,
       sup.reliability AS reliability, k.id AS component, pl.id AS plant, po.rate_wk AS rate_wk, po.qty AS qty,
       po.mode AS mode, po.first_arrival_day AS first_arrival_day, cs.spare_wk AS spare_wk,
       coalesce(cs.reserved_wk, 0) AS reserved_wk
ORDER BY po_id
