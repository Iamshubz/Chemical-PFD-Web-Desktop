export type Graph = {
  adjacencyList: Record<string, string[]>;
  inDegree: Record<string, number>;
  outDegree: Record<string, number>;
};

export function buildGraph(
  nodes: { id: string | number }[],
  connections: {
    sourceItemId: string | number;
    targetItemId: string | number;
  }[],
): Graph {
  const adjacencyList: Record<string, string[]> = {};
  const inDegree: Record<string, number> = {};
  const outDegree: Record<string, number> = {};

  // Initialize all nodes
  nodes.forEach((node) => {
    const id = String(node.id);
    adjacencyList[id] = [];
    inDegree[id] = 0;
    outDegree[id] = 0;
  });

  // Build edges
  connections.forEach((conn) => {
    const source = String(conn.sourceItemId);
    const target = String(conn.targetItemId);

    if (!adjacencyList[source] || !adjacencyList[target]) return;

    adjacencyList[source].push(target);
    outDegree[source]++;
    inDegree[target]++;
  });

  return { adjacencyList, inDegree, outDegree };
}
