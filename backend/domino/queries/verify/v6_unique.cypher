// V6: at most one PO per (decision, site, component, plant). Expected: no rows.
MATCH (d:Decision)-[c:CREATED]->(po:PurchaseOrder)-[fs:FROM_SITE]->(s:Site)
MATCH (po)-[fc:FOR_COMPONENT]->(k:Component)
MATCH (po)-[dt:DELIVERS_TO]->(pl:Plant)
WITH d, s, k, pl, count(po) AS n
WHERE n > 1
RETURN d.id AS decision, s.id AS site, k.id AS component, pl.id AS plant, n
