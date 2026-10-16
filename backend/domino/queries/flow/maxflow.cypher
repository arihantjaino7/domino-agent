// Q-MAXFLOW on the scratch graph. Returns only edges that carry flow (SPIKE #2); flows are floats.
// If the max flow is 0, `edges` is empty and no rows come back: the engine treats that as flow 0.
MATCH (s:F) WHERE s.id IN $source_ids
WITH collect(s) AS sources
MATCH (t:F {id: $sink_id})
CALL algo.maxFlow({sourceNodes: sources, targetNodes: [t], capacityProperty: $capacity_property,
                   relationshipTypes: ['CAP']})
YIELD edges, edgeFlows, maxFlow
UNWIND range(0, size(edges) - 1) AS i
RETURN startNode(edges[i]).id AS src, endNode(edges[i]).id AS dst, edgeFlows[i] AS flow, maxFlow AS max_flow
