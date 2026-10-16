// Seed loader: Sea and air ports. One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Port:Place)
SET n = r
RETURN count(n) AS created
