// Products at the plant that need $component_id, and the substitutes each one approves (ALLOWS_ALTERNATE).
MATCH (pl:Plant {id: $plant_id})-[b:BUILDS]->(p:Product)-[req:REQUIRES]->(k:Component {id: $component_id})
OPTIONAL MATCH (p)-[aa:ALLOWS_ALTERNATE]->(alt:Component)
WHERE aa.for_component = $component_id
RETURN p.id AS product, collect(DISTINCT alt.id) AS alternates
ORDER BY product
