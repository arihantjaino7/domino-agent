// Seed loader: Customer orders. One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Order)
SET n = r
RETURN count(n) AS created
