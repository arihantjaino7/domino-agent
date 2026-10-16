// Full-text lookup on every location (Site, Region, HazardZone, Port, Plant).
CALL db.idx.fulltext.queryNodes('Place', $term) YIELD node, score
RETURN node.id AS id, labels(node) AS labels, node.name AS name, score
ORDER BY score DESC, id
LIMIT 8
