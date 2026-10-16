// Seed loader: Finished products. One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Product)
SET n = r
RETURN count(n) AS created
