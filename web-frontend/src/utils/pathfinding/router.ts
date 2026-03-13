// src/utils/pathfinding/router.ts
import { CanvasItem } from '@/components/Canvas/types';
import { Point } from './types';
import { aStar } from './aStar';
import { toGrid, buildObstacleGrid, getGridBounds } from './grid';
import { getObstacleRects, applyStandoff } from './obstacles';
import { optimizePath } from './optimize';

/**
 * Configuration for the auto-router
 */
export interface RouterConfig {
    canvasWidth: number;
    canvasHeight: number;
    standoffDistance?: number;
}

/**
 * Find optimal orthogonal path between two points avoiding obstacles
 */
export function findOrthogonalPath(
    start: Point,
    end: Point,
    items: CanvasItem[],
    config: RouterConfig
): Point[] {
    const { canvasWidth, canvasHeight } = config;

    // Get obstacle rectangles from canvas items
    const obstacleRects = getObstacleRects(items);

    // Build obstacle grid
    const obstacleGrid = buildObstacleGrid(obstacleRects, canvasWidth, canvasHeight);
    const gridBounds = getGridBounds(canvasWidth, canvasHeight);

    // Convert start and end points to grid coordinates
    const startGrid = toGrid(start);
    const endGrid = toGrid(end);

    // Run A* pathfinding
    const result = aStar(startGrid, endGrid, obstacleGrid, gridBounds);

    if (!result.found || result.path.length === 0) {
        // Fallback: create simple orthogonal path
        return createFallbackPath(start, end);
    }

    // Optimize and convert path to canvas coordinates
    return optimizePath(result.path);
}

/**
 * Create a simple fallback path when A* fails
 */
function createFallbackPath(start: Point, end: Point): Point[] {
    // Create L-shaped path: horizontal then vertical
    const midX = (start.x + end.x) / 2;
    return [
        start,
        { x: midX, y: start.y },
        { x: midX, y: end.y },
        end,
    ];
}

/**
 * Enhanced routing that includes standoff distances and waypoints
 */
export function smartOrthogonalRoute(
    start: Point,
    end: Point,
    items: CanvasItem[],
    config: RouterConfig,
    startGrip?: any,
    endGrip?: any,
    waypoints?: Point[]
): Point[] {
    const { standoffDistance = 20 } = config;

    // Apply standoff distances
    const startWithStandoff = startGrip ? applyStandoff(start, startGrip, standoffDistance) : start;
    const endWithStandoff = endGrip ? applyStandoff(end, endGrip, standoffDistance) : end;

    if (!waypoints || waypoints.length === 0) {
        // Direct routing
        return findOrthogonalPath(startWithStandoff, endWithStandoff, items, config);
    } else {
        // Multi-segment routing with waypoints
        const fullPath: Point[] = [start];

        // Route from start to first waypoint
        const firstSegment = findOrthogonalPath(startWithStandoff, waypoints[0], items, config);
        fullPath.push(...firstSegment.slice(1)); // Skip duplicate start point

        // Route between intermediate waypoints
        for (let i = 0; i < waypoints.length - 1; i++) {
            const segment = findOrthogonalPath(waypoints[i], waypoints[i + 1], items, config);
            fullPath.push(...segment.slice(1)); // Skip duplicate connection point
        }

        // Route from last waypoint to end
        const lastSegment = findOrthogonalPath(waypoints[waypoints.length - 1], endWithStandoff, items, config);
        fullPath.push(...lastSegment.slice(1)); // Skip duplicate connection point

        fullPath.push(end);
        return fullPath;
    }
}