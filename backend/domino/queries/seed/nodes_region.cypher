// Seed loader: Real regions, the unit of geographic exposure. One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Region:Place)
SET n = r
RETURN count(n) AS created
