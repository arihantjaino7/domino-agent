// V1: no alternate source is committed beyond its spare_wk. Expected: no rows.
MATCH (po:PurchaseOrder)-[fs:FROM_SITE]->(s:Site)-[cs:CAN_SUPPLY]->(pl:Plant)
MATCH (po)-[dt:DELIVERS_TO]->(pl)
MATCH (po)-[fc:FOR_COMPONENT]->(k:Component)
WHERE k.id = cs.component_id AND po.status IN ['committed', 'in_transit']
WITH s, pl, cs, sum(po.rate_wk) AS committed
WHERE committed > cs.spare_wk
RETURN s.id AS site, pl.id AS plant, cs.component_id AS component, committed, cs.spare_wk AS spare
ORDER BY site, plant
