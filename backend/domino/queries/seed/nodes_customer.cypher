// Seed loader: Customers; strategic ones carry large daily late penalties. One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Customer)
SET n = r
RETURN count(n) AS created
