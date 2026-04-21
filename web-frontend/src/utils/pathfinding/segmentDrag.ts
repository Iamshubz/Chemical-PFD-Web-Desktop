// src/utils/pathfinding/segmentDrag.ts
// Path-based segment dragging utilities.
// The PATH (Point[]) is the single source of truth — not the rendered segments.

import { Point } from "./types";

/**
 * Snap a coordinate value to the nearest grid cell.
 */
export function snap(value: number, grid: number = 10): number {
  return Math.round(value / grid) * grid;
}

/**
 * Move a single orthogonal segment within a path.
 *
 * Vertical segments (p1.x === p2.x) are moved horizontally (dx).
 * Horizontal segments (p1.y === p2.y) are moved vertically (dy).
 *
 * The function immutably adjusts the two endpoints that form the dragged
 * segment, while keeping the points at segmentIndex and segmentIndex+1
 * connected to their respective neighbours via shared coordinate values.
 *
 * @param path         Full path array (at least 2 points)
 * @param segmentIndex Index of the FIRST point of the segment being dragged
 * @param dx           Horizontal drag delta
 * @param dy           Vertical drag delta
 * @returns New path array with the segment moved
 */
export function moveSegment(
  path: Point[],
  segmentIndex: number,
  dx: number,
  dy: number,
): Point[] {
  if (segmentIndex < 0 || segmentIndex >= path.length - 1) return path;

  // Deep-copy the path so we never mutate the original
  const newPath: Point[] = path.map((p) => ({ ...p }));

  const p1 = newPath[segmentIndex];
  const p2 = newPath[segmentIndex + 1];

  const isVertical = Math.abs(p1.x - p2.x) < 1; // same X → vertical segment

  if (isVertical) {
    // Move segment left/right
    p1.x += dx;
    p2.x += dx;

    // Propagate to the previous neighbour's shared X coordinate
    if (segmentIndex > 0) {
      newPath[segmentIndex - 1] = { ...newPath[segmentIndex - 1] };
      // previous segment ends at p1 — align its end X to stay connected
      // (only needed if the previous segment is horizontal, i.e. same Y)
      // No direct mutation needed: p1 IS the shared point already updated above
    }

    // Propagate to the next neighbour's shared X coordinate
    if (segmentIndex + 2 < newPath.length) {
      newPath[segmentIndex + 2] = { ...newPath[segmentIndex + 2] };
      // next segment starts at p2 — already updated above
    }
  } else {
    // Move segment up/down
    p1.y += dy;
    p2.y += dy;

    if (segmentIndex > 0) {
      newPath[segmentIndex - 1] = { ...newPath[segmentIndex - 1] };
    }
    if (segmentIndex + 2 < newPath.length) {
      newPath[segmentIndex + 2] = { ...newPath[segmentIndex + 2] };
    }
  }

  return newPath;
}

/**
 * Find the index of the first point in `path` that is part of the segment
 * closest to the provided segment endpoints (within tolerance).
 *
 * Returns -1 if no match found.
 */
export function findSegmentIndex(
  path: Point[],
  p1: Point,
  p2: Point,
  tolerance: number = 4,
): number {
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const p1Match =
      Math.abs(a.x - p1.x) < tolerance && Math.abs(a.y - p1.y) < tolerance;
    const p2Match =
      Math.abs(b.x - p2.x) < tolerance && Math.abs(b.y - p2.y) < tolerance;
    if (p1Match && p2Match) return i;
  }
  return -1;
}
