// Seed loader: Companies (legal entities). One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Supplier)
SET n = r
RETURN count(n) AS created
