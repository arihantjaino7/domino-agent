// Q-FLOW-EXTRACT (b): every FEEDS edge 1-4 hops above those tier-1 sites, with the source site's capacity.
// DISTINCT on the edge removes duplicates from overlapping paths (SPIKE #8).
MATCH (t1:Site)-[e:SUPPLIES|CAN_SUPPLY]->(:Plant {id: $plant_id})
WHERE e.component_id = $component_id
MATCH p = (:Site)-[:FEEDS*1..4]->(t1)
UNWIND relationships(p) AS f
WITH DISTINCT f
RETURN startNode(f).id AS src, endNode(f).id AS dst, f.component_id AS component, f.cap_wk AS cap_wk,
       f.used_wk AS used_wk, startNode(f).capacity_wk AS src_cap, startNode(f).capacity_factor AS src_factor
ORDER BY src, dst, component
