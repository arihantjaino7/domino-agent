// Scratch flow graph: one :F node per site half (<site>:in, <site>:out) plus the plant.
UNWIND $rows AS r
CREATE (n:F {id: r.id})
RETURN count(n) AS created
