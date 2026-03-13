// src/utils/pathfinding/aStar.ts
import { GridPoint, PathResult, AStarNode } from "./types";

/**
 * Priority queue implementation for A* algorithm
 */
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

/**
 * Manhattan distance heuristic for orthogonal movement
 */
function heuristic(a: GridPoint, b: GridPoint): number {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

/**
 * Get neighboring grid points (4-directional orthogonal movement)
 */
function getNeighbors(
  point: GridPoint,
  grid: boolean[][],
  bounds: { width: number; height: number },
): GridPoint[] {
  const neighbors: GridPoint[] = [];
  const directions = [
    { x: 1, y: 0 }, // Right
    { x: -1, y: 0 }, // Left
    { x: 0, y: 1 }, // Down
    { x: 0, y: -1 }, // Up
  ];

  for (const dir of directions) {
    const nx = point.x + dir.x;
    const ny = point.y + dir.y;

    // Check bounds
    if (nx >= 0 && nx < bounds.width && ny >= 0 && ny < bounds.height) {
      // Check if cell is not blocked
      if (!grid[ny][nx]) {
        neighbors.push({ x: nx, y: ny });
      }
    }
  }

  return neighbors;
}

/**
 * Check if two grid points are equal
 */
function pointsEqual(a: GridPoint, b: GridPoint): boolean {
  return a.x === b.x && a.y === b.y;
}

/**
 * A* pathfinding algorithm for orthogonal movement
 */
export function aStar(
  start: GridPoint,
  goal: GridPoint,
  grid: boolean[][],
  bounds: { width: number; height: number },
): PathResult {
  const openSet = new PriorityQueue<AStarNode>();
  const closedSet = new Set<string>();

  // Key function for tracking visited nodes
  const key = (point: GridPoint) => `${point.x},${point.y}`;

  // Initialize start node
  const startNode: AStarNode = {
    point: start,
    g: 0,
    h: heuristic(start, goal),
    f: heuristic(start, goal),
    parent: null,
  };

  openSet.enqueue(startNode, startNode.f);

  while (!openSet.isEmpty()) {
    const current = openSet.dequeue()!;

    // Check if we reached the goal
    if (pointsEqual(current.point, goal)) {
      // Reconstruct path
      const path: GridPoint[] = [];
      let node: AStarNode | null = current;

      while (node) {
        path.unshift(node.point);
        node = node.parent;
      }

      return { path, found: true };
    }

    const currentKey = key(current.point);

    if (closedSet.has(currentKey)) {
      continue;
    }
    closedSet.add(currentKey);

    // Explore neighbors
    const neighbors = getNeighbors(current.point, grid, bounds);

    for (const neighbor of neighbors) {
      const neighborKey = key(neighbor);

      if (closedSet.has(neighborKey)) {
        continue;
      }

      const g = current.g + 1; // Orthogonal movement cost = 1
      const h = heuristic(neighbor, goal);
      const f = g + h;

      const neighborNode: AStarNode = {
        point: neighbor,
        g,
        h,
        f,
        parent: current,
      };

      // Check if this neighbor is already in open set with better cost
      const existingNode = openSet.find((node) =>
        pointsEqual(node.point, neighbor),
      );

      if (!existingNode || g < existingNode.g) {
        openSet.enqueue(neighborNode, f);
      }
    }
  }

  // No path found
  return { path: [], found: false };
}
