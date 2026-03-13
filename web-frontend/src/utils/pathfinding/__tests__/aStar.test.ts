// src/utils/pathfinding/__tests__/aStar.test.ts
import { aStar } from "../aStar";

describe("A* Pathfinding", () => {
  test("finds direct path when no obstacles", () => {
    const grid = [
      [false, false, false],
      [false, false, false],
      [false, false, false],
    ];

    const result = aStar({ x: 0, y: 0 }, { x: 2, y: 2 }, grid, {
      width: 3,
      height: 3,
    });

    expect(result.found).toBe(true);
    expect(result.path).toEqual([
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 2, y: 0 },
      { x: 2, y: 1 },
      { x: 2, y: 2 },
    ]);
  });

  test("avoids obstacles", () => {
    const grid = [
      [false, false, false],
      [false, true, false], // obstacle at (1,1)
      [false, false, false],
    ];

    const result = aStar({ x: 0, y: 0 }, { x: 2, y: 2 }, grid, {
      width: 3,
      height: 3,
    });

    expect(result.found).toBe(true);
    // Should go around the obstacle
    expect(result.path.length).toBeGreaterThan(4); // longer path due to detour
  });

  test("returns no path when blocked", () => {
    const grid = [
      [false, true, false],
      [false, true, false],
      [false, true, false],
    ];

    const result = aStar({ x: 0, y: 0 }, { x: 2, y: 2 }, grid, {
      width: 3,
      height: 3,
    });

    expect(result.found).toBe(false);
    expect(result.path).toEqual([]);
  });
});
