// Seed loader: Kestrel assembly plants. One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Plant:Place)
SET n = r
RETURN count(n) AS created
