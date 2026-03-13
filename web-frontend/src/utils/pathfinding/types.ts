// src/utils/pathfinding/types.ts
export interface Point {
  x: number;
  y: number;
}

export interface GridPoint {
  x: number;
  y: number;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PathResult {
  path: GridPoint[];
  found: boolean;
}

export interface AStarNode {
  point: GridPoint;
  g: number; // Cost from start
  h: number; // Heuristic cost to end
  f: number; // Total cost (g + h)
  parent: AStarNode | null;
}
