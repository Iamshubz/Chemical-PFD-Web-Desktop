// src/utils/pathfinding/__tests__/grid.test.ts
import { toGrid, toCanvas, buildObstacleGrid } from "../grid";
import { Rect } from "../types";

describe("Grid Utilities", () => {
  test("converts canvas to grid coordinates", () => {
    const canvasPoint = { x: 50, y: 30 };
    const gridPoint = toGrid(canvasPoint);

    expect(gridPoint.x).toBe(2); // 50 / 20 = 2.5 -> floor to 2
    expect(gridPoint.y).toBe(1); // 30 / 20 = 1.5 -> floor to 1
  });

  test("converts grid to canvas coordinates", () => {
    const gridPoint = { x: 2, y: 1 };
    const canvasPoint = toCanvas(gridPoint);

    expect(canvasPoint.x).toBe(50); // 2 * 20 + 10 = 50
    expect(canvasPoint.y).toBe(30); // 1 * 20 + 10 = 30
  });

  test("builds obstacle grid from rectangles", () => {
    const obstacles: Rect[] = [
      { x: 0, y: 0, width: 40, height: 40 }, // Covers grid cells (0,0) to (1,1)
    ];

    const grid = buildObstacleGrid(obstacles, 100, 100);

    expect(grid[0][0]).toBe(true); // (0,0) should be blocked
    expect(grid[0][1]).toBe(true); // (1,0) should be blocked
    expect(grid[1][0]).toBe(true); // (0,1) should be blocked
    expect(grid[1][1]).toBe(true); // (1,1) should be blocked
    expect(grid[2][2]).toBe(false); // (2,2) should be free
  });
});
