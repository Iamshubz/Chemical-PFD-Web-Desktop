// src/utils/pathfinding/grid.ts
import { Point, GridPoint, Rect } from "./types";

/**
 * Grid system configuration
 */
export const GRID_SIZE = 20; // pixels per grid cell

/**
 * Convert canvas point to grid coordinates
 */
export function toGrid(point: Point): GridPoint {
    return {
        x: Math.floor(point.x / GRID_SIZE),
        y: Math.floor(point.y / GRID_SIZE),
    };
}

/**
 * Convert grid point to canvas coordinates (center of cell)
 */
export function toCanvas(gridPoint: GridPoint): Point {
    return {
        x: gridPoint.x * GRID_SIZE + GRID_SIZE / 2,
        y: gridPoint.y * GRID_SIZE + GRID_SIZE / 2,
    };
}

/**
 * Convert rectangle to grid bounds
 */
export function rectToGridBounds(rect: Rect): {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
} {
    const minX = Math.floor(rect.x / GRID_SIZE);
    const minY = Math.floor(rect.y / GRID_SIZE);
    const maxX = Math.floor((rect.x + rect.width - 1) / GRID_SIZE);
    const maxY = Math.floor((rect.y + rect.height - 1) / GRID_SIZE);

    return { minX, minY, maxX, maxY };
}

/**
 * Build obstacle grid from canvas items
 */
export function buildObstacleGrid(
    obstacles: Rect[],
    canvasWidth: number,
    canvasHeight: number,
): boolean[][] {
    const cols = Math.ceil(canvasWidth / GRID_SIZE);
    const rows = Math.ceil(canvasHeight / GRID_SIZE);

    // Initialize grid (false = free, true = blocked)
    const grid: boolean[][] = Array(rows)
        .fill(null)
        .map(() => Array(cols).fill(false));

    // Mark obstacles
    for (const obstacle of obstacles) {
        const bounds = rectToGridBounds(obstacle);

        for (let y = bounds.minY; y <= bounds.maxY; y++) {
            for (let x = bounds.minX; x <= bounds.maxX; x++) {
                if (y >= 0 && y < rows && x >= 0 && x < cols) {
                    grid[y][x] = true;
                }
            }
        }
    }

    return grid;
}

/**
 * Get grid bounds for a canvas
 */
export function getGridBounds(
    canvasWidth: number,
    canvasHeight: number,
): { width: number; height: number } {
    return {
        width: Math.ceil(canvasWidth / GRID_SIZE),
        height: Math.ceil(canvasHeight / GRID_SIZE),
    };
}
