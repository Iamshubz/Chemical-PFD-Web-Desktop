import { Graph } from "./buildGraph";

export type ValidationResult = {
  isolated: string[];
  circular: string[];
  brokenFlow: string[];
  hasInlet: boolean;
  hasOutlet: boolean;
};

export function validateGraph(graph: Graph): ValidationResult {
  const { adjacencyList, inDegree, outDegree } = graph;

  const isolated: string[] = [];
  const circular: Set<string> = new Set();
  const brokenFlow: string[] = [];

  const nodes = Object.keys(adjacencyList);

  if (nodes.length === 0) {
    return {
      isolated: [],
      circular: [],
      brokenFlow: [],
      hasInlet: false,
      hasOutlet: false,
    };
  }

  // 🔹 1. Isolated Nodes
  nodes.forEach((node) => {
    if (inDegree[node] === 0 && outDegree[node] === 0) {
      isolated.push(node);
    }
  });

  // 🔹 2. Inlet & Outlet Detection
  const inletNodes = nodes.filter(
    (node) => inDegree[node] === 0 && outDegree[node] > 0,
  );

  const outletNodes = nodes.filter(
    (node) => outDegree[node] === 0 && inDegree[node] > 0,
  );

  const hasInlet = inletNodes.length > 0;
  const hasOutlet = outletNodes.length > 0;

  // 🔹 3. Cycle Detection (DFS)
  const visited = new Set<string>();
  const recursionStack = new Set<string>();

  function dfs(node: string) {
    if (recursionStack.has(node)) {
      circular.add(node);
      return;
    }

    if (visited.has(node)) return;

    visited.add(node);
    recursionStack.add(node);

    for (const neighbor of adjacencyList[node]) {
      dfs(neighbor);
    }

    recursionStack.delete(node);
  }

  nodes.forEach((node) => {
    if (!visited.has(node)) {
      dfs(node);
    }
  });

  // 🔹 4. Continuous Flow (BFS from Inlets)
  const reachable = new Set<string>();
  const queue: string[] = [...inletNodes];

  while (queue.length > 0) {
    const current = queue.shift()!;
    reachable.add(current);

    for (const neighbor of adjacencyList[current]) {
      if (!reachable.has(neighbor)) {
        queue.push(neighbor);
      }
    }
  }

  nodes.forEach((node) => {
    if (!reachable.has(node) && !isolated.includes(node)) {
      brokenFlow.push(node);
    }
  });

  return {
    isolated,
    circular: Array.from(circular),
    brokenFlow,
    hasInlet,
    hasOutlet,
  };
}
