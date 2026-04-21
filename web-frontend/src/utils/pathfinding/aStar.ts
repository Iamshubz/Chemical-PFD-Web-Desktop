// src/utils/pathfinding/aStar.ts
import { Point, SpatialNode } from "./types";

export interface SpatialAStarNode {
  nodeId: string;
  g: number;
  h: number;
  f: number;
  parent: SpatialAStarNode | null;
  direction: 'horizontal' | 'vertical' | null;
  turns: number; // Number of direction changes so far (max 2 enforced)
}

class PriorityQueue<T> {
  private items: { item: T; priority: number }[] = [];

  enqueue(item: T, priority: number): void {
    this.items.push({ item, priority });
    this.items.sort((a, b) => a.priority - b.priority);
  }

  dequeue(): T | undefined {
    return this.items.shift()?.item;
  }

  isEmpty(): boolean {
    return this.items.length === 0;
  }

  contains(item: T, comparator: (a: T, b: T) => boolean): boolean {
    return this.items.some(({ item: queueItem }) =>
      comparator(item, queueItem),
    );
  }

  find(comparator: (item: T) => boolean): T | undefined {
    return this.items.find(({ item }) => comparator(item))?.item;
  }
}

function heuristic(a: SpatialNode, b: SpatialNode): number {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

export function aStarSpatial(
  startId: string,
  goalId: string,
  nodes: Map<string, SpatialNode>,
): { path: Point[]; found: boolean } {
  const startNodeData = nodes.get(startId);
  const goalNodeData = nodes.get(goalId);

  if (!startNodeData || !goalNodeData) return { path: [], found: false };

  const openSet = new PriorityQueue<SpatialAStarNode>();
  
  // We need to track closed set by nodeId AND incoming direction to allow 
  // revisiting a node if we approach it from a better direction (e.g. fewer bends).
  // However, simpler standard A* over graphs typically just records the best G per state.
  // State = nodeId + direction.
  const bestG = new Map<string, number>();

  const startState: SpatialAStarNode = {
    nodeId: startId,
    g: 0,
    h: heuristic(startNodeData, goalNodeData),
    f: heuristic(startNodeData, goalNodeData),
    parent: null,
    direction: null,
    turns: 0,
  };

  openSet.enqueue(startState, startState.f);
  bestG.set(`${startId}-null-0`, 0);

  while (!openSet.isEmpty()) {
    const current = openSet.dequeue()!;

    if (current.nodeId === goalId) {
      // Reconstruct Path
      const path: Point[] = [];
      let c: SpatialAStarNode | null = current;
      while (c) {
        const p = nodes.get(c.nodeId);
        if (p) path.unshift({ x: p.x, y: p.y });
        c = c.parent;
      }
      return { path, found: true };
    }

    const currentGraphNode = nodes.get(current.nodeId)!;

    for (const neighbor of currentGraphNode.neighbors) {
      const neighborGraphNode = nodes.get(neighbor.nodeId);
      if (!neighborGraphNode) continue;

      // Compute new turn count
      let newTurns = current.turns;
      if (current.direction !== null && current.direction !== neighbor.direction) {
        newTurns++;
      }

      // HARD CONSTRAINT: prune paths with more than 2 turns
      if (newTurns > 2) continue;

      const tentativeG = current.g + neighbor.distance;
      // State key includes turns so different turn-count paths to the same node are tracked separately
      const stateKey = `${neighbor.nodeId}-${neighbor.direction}-${newTurns}`;

      if (!bestG.has(stateKey) || tentativeG < bestG.get(stateKey)!) {
        bestG.set(stateKey, tentativeG);
        
        const h = heuristic(neighborGraphNode, goalNodeData);
        
        const nextState: SpatialAStarNode = {
          nodeId: neighbor.nodeId,
          g: tentativeG,
          h: h,
          f: tentativeG + h,
          parent: current,
          direction: neighbor.direction,
          turns: newTurns,
        };
        
        openSet.enqueue(nextState, nextState.f);
      }
    }
  }

  return { path: [], found: false };
}
