// Same-family components built from the same input as $component_id (e.g. DSP-14-HB for DSP-14).
// They are listed as candidates so the BOM check can reject them explicitly.
MATCH (k:Component {id: $component_id})-[m1:MADE_FROM]->(x:Component)<-[m2:MADE_FROM]-(c:Component)
WHERE c.id <> k.id AND c.family = k.family
RETURN DISTINCT c.id AS component
ORDER BY component
