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

  test("produces at most 2 turns (L or Z shape)", () => {
    // Build a 3x3 grid with full connectivity — multiple paths available
    // The max-turns constraint must limit the winning path to ≤2 bends
    const nodes = new Map<string, SpatialNode>();
    const positions = [
      [0,0],[1,0],[2,0],
      [0,1],[1,1],[2,1],
      [0,2],[1,2],[2,2],
    ];
    const getId = (x: number, y: number) => `${x},${y}`;
    for (const [x, y] of positions) {
      const neighbors: SpatialNode['neighbors'] = [];
      if (x > 0) neighbors.push({ nodeId: getId(x-1,y), distance:1, direction:'horizontal' });
      if (x < 2) neighbors.push({ nodeId: getId(x+1,y), distance:1, direction:'horizontal' });
      if (y > 0) neighbors.push({ nodeId: getId(x,y-1), distance:1, direction:'vertical' });
      if (y < 2) neighbors.push({ nodeId: getId(x,y+1), distance:1, direction:'vertical' });
      nodes.set(getId(x,y), { id: getId(x,y), x, y, neighbors });
    }

    const result = aStarSpatial("0,0", "2,2", nodes);
    expect(result.found).toBe(true);

    // Count direction changes in the returned path
    let turns = 0;
    for (let i = 1; i < result.path.length - 1; i++) {
      const prev = result.path[i - 1];
      const curr = result.path[i];
      const next = result.path[i + 1];
      const dirA = curr.x !== prev.x ? 'h' : 'v';
      const dirB = next.x !== curr.x ? 'h' : 'v';
      if (dirA !== dirB) turns++;
    }
    expect(turns).toBeLessThanOrEqual(2);
  });

  test("returns no path if only route requires more than 2 turns", () => {
    // A maze that forces 3+ turns with no shortcut — A* must fail under max-2 constraint
    // Layout: start=A, must zigzag 3 times to reach B with no direct route
    //   A-a-b
    //       |
    //   d-c-+   <- forced 3-turn path
    //   |
    //   e-B
    const nodes = new Map<string, SpatialNode>();
    nodes.set("0,0", { id:"0,0", x:0, y:0, neighbors:[{nodeId:"1,0",distance:1,direction:'horizontal'}] }); // A
    nodes.set("1,0", { id:"1,0", x:1, y:0, neighbors:[{nodeId:"0,0",distance:1,direction:'horizontal'},{nodeId:"2,0",distance:1,direction:'horizontal'}] });
    nodes.set("2,0", { id:"2,0", x:2, y:0, neighbors:[{nodeId:"1,0",distance:1,direction:'horizontal'},{nodeId:"2,1",distance:1,direction:'vertical'}] });
    nodes.set("2,1", { id:"2,1", x:2, y:1, neighbors:[{nodeId:"2,0",distance:1,direction:'vertical'},{nodeId:"1,1",distance:1,direction:'horizontal'}] });
    nodes.set("1,1", { id:"1,1", x:1, y:1, neighbors:[{nodeId:"2,1",distance:1,direction:'horizontal'},{nodeId:"0,1",distance:1,direction:'horizontal'}] });
    nodes.set("0,1", { id:"0,1", x:0, y:1, neighbors:[{nodeId:"1,1",distance:1,direction:'horizontal'},{nodeId:"0,2",distance:1,direction:'vertical'}] });
    nodes.set("0,2", { id:"0,2", x:0, y:2, neighbors:[{nodeId:"0,1",distance:1,direction:'vertical'},{nodeId:"1,2",distance:1,direction:'horizontal'}] });
    nodes.set("1,2", { id:"1,2", x:1, y:2, neighbors:[{nodeId:"0,2",distance:1,direction:'horizontal'}] }); // B

    const result = aStarSpatial("0,0", "1,2", nodes);
    // Only path requires H→V→H→V = 3 turns, which exceeds the max-2 limit
    expect(result.found).toBe(false);
  });
});

