// Q-RESOLVE: full-text lookup over every location (exact or fuzzy term; the caller adds %...%).
CALL db.idx.fulltext.queryNodes('Place', $term) YIELD node, score
RETURN node.id AS id, labels(node) AS labels, node.name AS name, node.country AS country, score
ORDER BY score DESC, id
LIMIT 5
