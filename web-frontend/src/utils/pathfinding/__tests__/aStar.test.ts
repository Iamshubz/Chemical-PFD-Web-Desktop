// src/utils/pathfinding/__tests__/aStar.test.ts
import { aStarSpatial } from "../aStar";
import { SpatialNode } from "../types";

describe("A* Spatial Pathfinding", () => {
  test("finds direct path in graph", () => {
    const nodes = new Map<string, SpatialNode>();
    
    nodes.set("0,0", { id: "0,0", x: 0, y: 0, neighbors: [{ nodeId: "1,0", distance: 1, direction: 'horizontal' }, { nodeId: "0,1", distance: 1, direction: 'vertical' }] });
    nodes.set("1,0", { id: "1,0", x: 1, y: 0, neighbors: [{ nodeId: "0,0", distance: 1, direction: 'horizontal' }, { nodeId: "2,0", distance: 1, direction: 'horizontal' }] });
    nodes.set("2,0", { id: "2,0", x: 2, y: 0, neighbors: [{ nodeId: "1,0", distance: 1, direction: 'horizontal' }, { nodeId: "2,1", distance: 1, direction: 'vertical' }] });
    
    nodes.set("0,1", { id: "0,1", x: 0, y: 1, neighbors: [{ nodeId: "0,0", distance: 1, direction: 'vertical' }, { nodeId: "0,2", distance: 1, direction: 'vertical' }] });
    nodes.set("2,1", { id: "2,1", x: 2, y: 1, neighbors: [{ nodeId: "2,0", distance: 1, direction: 'vertical' }, { nodeId: "2,2", distance: 1, direction: 'vertical' }] });

    nodes.set("0,2", { id: "0,2", x: 0, y: 2, neighbors: [{ nodeId: "0,1", distance: 1, direction: 'vertical' }, { nodeId: "1,2", distance: 1, direction: 'horizontal' }] });
    nodes.set("1,2", { id: "1,2", x: 1, y: 2, neighbors: [{ nodeId: "0,2", distance: 1, direction: 'horizontal' }, { nodeId: "2,2", distance: 1, direction: 'horizontal' }] });
    nodes.set("2,2", { id: "2,2", x: 2, y: 2, neighbors: [{ nodeId: "1,2", distance: 1, direction: 'horizontal' }, { nodeId: "2,1", distance: 1, direction: 'vertical' }] });

    const result = aStarSpatial("0,0", "2,2", nodes);

    expect(result.found).toBe(true);
    // Path should go to 2,0 then 2,2 (1 bend) or 0,2 then 2,2 (1 bend) to avoid directional penalties.
    expect(result.path.length).toBeGreaterThan(0);
  });

  test("returns no path when blocked", () => {
    const nodes = new Map<string, SpatialNode>();
    
    nodes.set("0,0", { id: "0,0", x: 0, y: 0, neighbors: [] }); // isolated
    nodes.set("2,2", { id: "2,2", x: 2, y: 2, neighbors: [] });

    const result = aStarSpatial("0,0", "2,2", nodes);

    expect(result.found).toBe(false);
    expect(result.path).toEqual([]);
  });
});
