// Q-EXPOSURE: multi-tier exposure of unknown depth, with the evidence path for every hit.
// *0..4 includes the affected site itself when it is a tier-1 supplier.
// One row per (chain, tier-1, component, product, plant); orders are collected per row.
MATCH (inc:Incident {id: $incident_id})-[a:AFFECTS]->(d:Site)
MATCH chain = (d)-[:FEEDS*0..4]->(t1:Site)
MATCH (t1)-[sup:SUPPLIES]->(pl:Plant)-[b:BUILDS]->(prod:Product)-[req:REQUIRES]->(k:Component)
WHERE k.id = sup.component_id
MATCH (o:Order)-[fp:FOR_PRODUCT]->(prod)
MATCH (o)-[fa:FULFILLED_AT]->(pl)
WHERE o.status = 'open' AND o.need_day <= $horizon
RETURN d.id AS origin, [n IN nodes(chain) | n.id] AS supply_path, length(chain) AS upstream_hops,
       t1.id AS tier1, k.id AS component, prod.id AS product, pl.id AS plant,
       collect(o.id) AS orders, sum(o.value_cents) AS value_cents
ORDER BY origin, tier1, plant, component, product, upstream_hops
