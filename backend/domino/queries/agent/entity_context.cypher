// An entity's properties and its 1-hop neighbourhood (get_entity_context).
MATCH (n {id: $entity_id})
OPTIONAL MATCH (n)-[r]-(m)
RETURN properties(n) AS props, labels(n) AS labels, type(r) AS rel, startNode(r) = n AS outgoing,
       m.id AS other, labels(m) AS other_labels, properties(r) AS rel_props
LIMIT 60
