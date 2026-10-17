// Canvas: plants and the products each builds.
MATCH (pl:Plant)
OPTIONAL MATCH (pl)-[b:BUILDS]->(p:Product)
RETURN pl.id AS id, pl.name AS name, pl.country AS country, collect(p.id) AS products
ORDER BY id
