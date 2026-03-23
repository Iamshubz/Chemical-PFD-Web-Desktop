// src/utils/pathfinding/spatialGraph.ts
import { Point, SpatialNode } from "./types";
import { CanvasItem } from "@/components/Canvas/types";
import { getPaddedObstacleRects, orthogonalSegmentHitsObstacle } from "./obstacles";
import { getGripPosition } from "../routing"; // We may need to get grips from here

export function generateSpatialGraph(
  items: CanvasItem[],
  startPoint: Point,
  endPoint: Point,
  waypoints: Point[] = [],
  padding: number = 20,
  canvasWidth: number = 2000,
  canvasHeight: number = 1500
): Map<string, SpatialNode> {
  const rects = getPaddedObstacleRects(items, padding);

  // 1. Gather all "Lead Lines" coordinates (X and Y separately)
  const xCoords = new Set<number>();
  const yCoords = new Set<number>();

  // Add canvas borders (with slight padding inward so lines don't get stuck exactly on edge)
  xCoords.add(10);
  xCoords.add(canvasWidth - 10);
  yCoords.add(10);
  yCoords.add(canvasHeight - 10);

  // Add Start, End, and Waypoints
  const keyPoints = [startPoint, endPoint, ...waypoints];
  for (const p of keyPoints) {
    xCoords.add(p.x);
    yCoords.add(p.y);
  }

  // Add Item grips and padded corners
  for (const item of items) {
    // Add padded corners
    const { x: renderX, y: renderY, width: renderWidth, height: renderHeight } = getPaddedObstacleRects([item], padding)[0];
    xCoords.add(renderX);
    xCoords.add(renderX + renderWidth);
    yCoords.add(renderY);
    yCoords.add(renderY + renderHeight);

    // Add grips
    if (item.grips) {
      for (let i = 0; i < item.grips.length; i++) {
        const gripPos = getGripPosition(item, i);
        if (gripPos) {
          xCoords.add(gripPos.x);
          yCoords.add(gripPos.y);
        }
      }
    }
  }

  // Convert to sorted arrays
  const sortedX = Array.from(xCoords).sort((a, b) => a - b);
  const sortedY = Array.from(yCoords).sort((a, b) => a - b);

  // 2. Generate Grid Intersections (Spatial Nodes) map
  const nodes = new Map<string, SpatialNode>();
  
  // Helper to check if a point is inside any padded obstacle
  const isInsideObstacle = (p: Point) => {
    // If it's a start/end/waypoint, allow it even if marginally inside
    for (const kp of keyPoints) {
      if (Math.abs(kp.x - p.x) < 2 && Math.abs(kp.y - p.y) < 2) return false;
    }

    for (const r of rects) {
      // Must be STRICTLY inside to be disqualified. Bounding edges are navigable.
      if (p.x > r.x && p.x < r.x + r.width && p.y > r.y && p.y < r.y + r.height) {
        return true;
      }
    }
    return false;
  };

  // Create valid nodes
  for (const y of sortedY) {
    for (const x of sortedX) {
      if (!isInsideObstacle({ x, y })) {
        const id = `${x},${y}`;
        nodes.set(id, {
          id,
          x,
          y,
          neighbors: []
        });
      }
    }
  }

  // 3. Connect Horizontal & Vertical neighbors
  // Connect horizontally
  for (const y of sortedY) {
    let prevNode: SpatialNode | null = null;
    for (const x of sortedX) {
      const node = nodes.get(`${x},${y}`);
      if (node) {
        if (prevNode) {
          // Check if the segment crosses any obstacle
          let hitsObstacle = false;
          if (orthogonalSegmentHitsObstacle(prevNode, node, rects)) {
            hitsObstacle = true;
          }

          if (!hitsObstacle) {
            const dist = Math.abs(node.x - prevNode.x);
            prevNode.neighbors.push({ nodeId: node.id, distance: dist, direction: 'horizontal' });
            node.neighbors.push({ nodeId: prevNode.id, distance: dist, direction: 'horizontal' });
          }
        }
        prevNode = node;
      } else {
        prevNode = null; // Path blocked, break continuity
      }
    }
  }

  // Connect vertically
  for (const x of sortedX) {
    let prevNode: SpatialNode | null = null;
    for (const y of sortedY) {
      const node = nodes.get(`${x},${y}`);
      if (node) {
        if (prevNode) {
          let hitsObstacle = false;
          if (orthogonalSegmentHitsObstacle(prevNode, node, rects)) {
            hitsObstacle = true;
          }

          if (!hitsObstacle) {
            const dist = Math.abs(node.y - prevNode.y);
            prevNode.neighbors.push({ nodeId: node.id, distance: dist, direction: 'vertical' });
            node.neighbors.push({ nodeId: prevNode.id, distance: dist, direction: 'vertical' });
          }
        }
        prevNode = node;
      } else {
        prevNode = null; // Path blocked
      }
    }
  }

  return nodes;
}
