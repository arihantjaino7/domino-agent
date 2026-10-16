// The upstream FEEDS sub-DAG (1-4 hops) above every site that supplies a plant.
// DISTINCT on the edge removes the duplicates that come from several paths sharing an edge.
MATCH (t1:Site)-[sup:SUPPLIES]->(:Plant)
MATCH p = (:Site)-[:FEEDS*1..4]->(t1)
UNWIND relationships(p) AS f
WITH DISTINCT f
RETURN startNode(f).id AS src, endNode(f).id AS dst, f.component_id AS component,
       f.used_wk AS used_wk, f.cap_wk AS cap_wk
ORDER BY src, dst, component
