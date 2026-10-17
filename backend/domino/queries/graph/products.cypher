// Canvas: products.
MATCH (p:Product)
RETURN p.id AS id, p.name AS name
ORDER BY id
