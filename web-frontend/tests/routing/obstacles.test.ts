/**
 * tests/routing/obstacles.test.ts
 *
 * Unit tests for src/utils/pathfinding/obstacles.ts
 *
 * Covers:
 *  1. getPaddedObstacleRects — expansion math
 *  2. segmentHitsObstacle — AABB overlap detection
 *  3. orthogonalSegmentHitsObstacle — strict H/V collision
 *  4. pathHitsObstacle — full-path validation
 *  5. applyStandoff — standoff point derivation
 *  6. Simulated PFD canvas with E01 + C01A/B bounding boxes
 */

import { describe, it, expect, vi } from 'vitest';

// Mock calculateAspectFit so items are treated as full-container rectangles
vi.mock('@/utils/layout', () => ({
  calculateAspectFit: vi.fn(
    (containerW: number, containerH: number) => ({
      x: 0,
      y: 0,
      width: containerW,
      height: containerH,
    }),
  ),
}));

import {
  getObstacleRects,
  getPaddedObstacleRects,
  segmentHitsObstacle,
  orthogonalSegmentHitsObstacle,
  pathHitsObstacle,
  applyStandoff,
} from '@/utils/pathfinding/obstacles';

import type { CanvasItem } from '@/components/Canvas/types';

// ──────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────

function makeItem(
  id: number,
  x: number,
  y: number,
  w: number,
  h: number,
): CanvasItem {
  return {
    id,
    x,
    y,
    width: w,
    height: h,
    rotation: 0,
    sequence: id,
    addedAt: 0,
    component_id: id,
    name: `item-${id}`,
    icon: '',
    svg: '',
    class: '',
    object: '',
    args: [],
    naturalWidth: w,
    naturalHeight: h,
  };
}

// ──────────────────────────────────────────────────────────
// 1. getObstacleRects
// ──────────────────────────────────────────────────────────
describe('getObstacleRects', () => {
  it('maps each item to a bounding rect with correct position and size', () => {
    const item = makeItem(1, 100, 200, 150, 80);
    const rects = getObstacleRects([item]);
    expect(rects).toHaveLength(1);
    expect(rects[0]).toEqual({ x: 100, y: 200, width: 150, height: 80 });
  });

  it('returns an empty array for no items', () => {
    expect(getObstacleRects([])).toEqual([]);
  });
});

// ──────────────────────────────────────────────────────────
// 2. getPaddedObstacleRects (Collision Math)
// ──────────────────────────────────────────────────────────
describe('getPaddedObstacleRects', () => {
  /**
   * Simulated PFD layout:
   *   E01 Reactor:  x=400, y=300, w=200, h=200  → padded (pad=20): x=380, y=280, w=240, h=240
   *   C01A:         x=100, y=350, w=100, h=100  → padded:          x=80,  y=330, w=140, h=140
   *   C01B:         x=700, y=350, w=100, h=100  → padded:          x=680, y=330, w=140, h=140
   */
  const E01 = makeItem(1, 400, 300, 200, 200);
  const C01A = makeItem(2, 100, 350, 100, 100);
  const C01B = makeItem(3, 700, 350, 100, 100);

  it('expands E01 correctly with 20px padding', () => {
    const [r] = getPaddedObstacleRects([E01], 20);
    expect(r.x).toBe(380);
    expect(r.y).toBe(280);
    expect(r.width).toBe(240);
    expect(r.height).toBe(240);
  });

  it('expands C01A correctly with 20px padding', () => {
    const rects = getPaddedObstacleRects([C01A], 20);
    expect(rects[0]).toEqual({ x: 80, y: 330, width: 140, height: 140 });
  });

  it('expands C01B correctly with 20px padding', () => {
    const rects = getPaddedObstacleRects([C01B], 20);
    expect(rects[0]).toEqual({ x: 680, y: 330, width: 140, height: 140 });
  });

  it('produces three padded rects for three items', () => {
    const rects = getPaddedObstacleRects([E01, C01A, C01B], 20);
    expect(rects).toHaveLength(3);
  });

  it('custom padding=0 leaves rects unchanged', () => {
    const rects = getPaddedObstacleRects([E01], 0);
    expect(rects[0]).toEqual({ x: 400, y: 300, width: 200, height: 200 });
  });
});

// ──────────────────────────────────────────────────────────
// 3. segmentHitsObstacle
// ──────────────────────────────────────────────────────────
describe('segmentHitsObstacle', () => {
  const obstacle = { x: 400, y: 300, width: 200, height: 200 }; // E01

  it('detects a horizontal segment passing directly through E01', () => {
    // Horizontal line at y=400 (mid-height) from x=200 to x=700 — slices through E01
    const hits = segmentHitsObstacle({ x: 200, y: 400 }, { x: 700, y: 400 }, [obstacle]);
    expect(hits).toBe(true);
  });

  it('does NOT flag a horizontal segment clearly above E01', () => {
    // y=250 < 300 (top of E01)
    const hits = segmentHitsObstacle({ x: 200, y: 250 }, { x: 700, y: 250 }, [obstacle]);
    expect(hits).toBe(false);
  });

  it('does NOT flag a horizontal segment clearly below E01', () => {
    // y=550 > 500 (bottom of E01)
    const hits = segmentHitsObstacle({ x: 200, y: 550 }, { x: 700, y: 550 }, [obstacle]);
    expect(hits).toBe(false);
  });

  it('detects a vertical segment passing through E01', () => {
    // Vertical line at x=500 from y=100 to y=700 — passes through E01
    const hits = segmentHitsObstacle({ x: 500, y: 100 }, { x: 500, y: 700 }, [obstacle]);
    expect(hits).toBe(true);
  });

  it('returns false for an empty obstacles array', () => {
    expect(segmentHitsObstacle({ x: 0, y: 0 }, { x: 1000, y: 1000 }, [])).toBe(false);
  });
});

// ──────────────────────────────────────────────────────────
// 4. orthogonalSegmentHitsObstacle (strict H/V collision check)
// ──────────────────────────────────────────────────────────
describe('orthogonalSegmentHitsObstacle', () => {
  const obstacle = { x: 400, y: 300, width: 200, height: 200 }; // E01 padded

  describe('vertical segments (same X)', () => {
    it('detects when vertical segment passes through obstacle interior', () => {
      // x=500 is strictly inside [400..600], y range [100..700] spans [300..500]
      const hits = orthogonalSegmentHitsObstacle(
        { x: 500, y: 100 },
        { x: 500, y: 700 },
        [obstacle],
      );
      expect(hits).toBe(true);
    });

    it('does NOT flag vertical segment at left edge of obstacle (x = obstacle.x)', () => {
      // x=400 is on the boundary, not strictly inside (> r.x required)
      const hits = orthogonalSegmentHitsObstacle(
        { x: 400, y: 100 },
        { x: 400, y: 700 },
        [obstacle],
      );
      expect(hits).toBe(false);
    });

    it('does NOT flag vertical segment at right edge (x = obstacle.x + width)', () => {
      const hits = orthogonalSegmentHitsObstacle(
        { x: 600, y: 100 },
        { x: 600, y: 700 },
        [obstacle],
      );
      expect(hits).toBe(false);
    });

    it('does NOT flag vertical segment entirely to the left of obstacle', () => {
      const hits = orthogonalSegmentHitsObstacle(
        { x: 300, y: 100 },
        { x: 300, y: 700 },
        [obstacle],
      );
      expect(hits).toBe(false);
    });

    it('does NOT flag vertical segment that spans y range BELOW obstacle (no overlap)', () => {
      // x=500 inside obstacle, but y range [520..700] is below obstacle max y=500
      const hits = orthogonalSegmentHitsObstacle(
        { x: 500, y: 520 },
        { x: 500, y: 700 },
        [obstacle],
      );
      expect(hits).toBe(false);
    });
  });

  describe('horizontal segments (same Y)', () => {
    it('detects when horizontal segment passes through obstacle interior', () => {
      // y=400 strictly inside [300..500], x range [200..700] spans [400..600]
      const hits = orthogonalSegmentHitsObstacle(
        { x: 200, y: 400 },
        { x: 700, y: 400 },
        [obstacle],
      );
      expect(hits).toBe(true);
    });

    it('does NOT flag horizontal segment at top edge (y = obstacle.y)', () => {
      const hits = orthogonalSegmentHitsObstacle(
        { x: 200, y: 300 },
        { x: 700, y: 300 },
        [obstacle],
      );
      expect(hits).toBe(false);
    });

    it('does NOT flag horizontal segment clearly above obstacle', () => {
      const hits = orthogonalSegmentHitsObstacle(
        { x: 200, y: 100 },
        { x: 700, y: 100 },
        [obstacle],
      );
      expect(hits).toBe(false);
    });

    it('does NOT flag horizontal segment that spans x BEFORE obstacle', () => {
      // y=400 inside obstacle, but x range [100..380] is to the left of obstacle x=400
      const hits = orthogonalSegmentHitsObstacle(
        { x: 100, y: 400 },
        { x: 380, y: 400 },
        [obstacle],
      );
      expect(hits).toBe(false);
    });
  });
});

// ──────────────────────────────────────────────────────────
// 5. pathHitsObstacle
// ──────────────────────────────────────────────────────────
describe('pathHitsObstacle', () => {
  const e01 = { x: 400, y: 300, width: 200, height: 200 };

  it('detects a path that passes through E01', () => {
    const path = [
      { x: 200, y: 400 },
      { x: 700, y: 400 }, // Direct horizontal path through E01
    ];
    expect(pathHitsObstacle(path, [e01])).toBe(true);
  });

  it('does NOT flag a path that routes above E01', () => {
    const path = [
      { x: 200, y: 250 }, // y=250 < 300 (above E01)
      { x: 700, y: 250 },
    ];
    expect(pathHitsObstacle(path, [e01])).toBe(false);
  });

  it('does NOT flag a path that routes below E01', () => {
    const path = [
      { x: 200, y: 550 }, // y=550 > 500 (below E01)
      { x: 700, y: 550 },
    ];
    expect(pathHitsObstacle(path, [e01])).toBe(false);
  });

  it('returns false for an empty path', () => {
    expect(pathHitsObstacle([], [e01])).toBe(false);
  });

  it('returns false for a single-point path', () => {
    expect(pathHitsObstacle([{ x: 500, y: 400 }], [e01])).toBe(false);
  });

  it('L-shaped path that detours above E01 does not hit obstacle', () => {
    // Route: C01A right grip → go up to y=250 → go right → go back down
    const path = [
      { x: 200, y: 400 },
      { x: 200, y: 250 }, // go up above E01
      { x: 700, y: 250 }, // traverse right above E01
      { x: 700, y: 400 }, // go back down to C01B
    ];
    expect(pathHitsObstacle(path, [e01])).toBe(false);
  });
});

// ──────────────────────────────────────────────────────────
// 6. applyStandoff
// ──────────────────────────────────────────────────────────
describe('applyStandoff', () => {
  const point = { x: 500, y: 400 };
  const dist = 20;

  it('applies standoff to the left for a left grip', () => {
    const grip = { x: 5, y: 50 }; // near left
    const result = applyStandoff(point, grip, dist);
    expect(result).toEqual({ x: 480, y: 400 });
  });

  it('applies standoff to the right for a right grip', () => {
    const grip = { x: 95, y: 50 }; // near right
    const result = applyStandoff(point, grip, dist);
    expect(result).toEqual({ x: 520, y: 400 });
  });

  it('applies standoff upward for a top grip (negative Y direction)', () => {
    const grip = { x: 50, y: 95 }; // near top (y=100 is top in grip space)
    const result = applyStandoff(point, grip, dist);
    expect(result).toEqual({ x: 500, y: 380 });
  });

  it('applies standoff downward for a bottom grip (positive Y direction)', () => {
    const grip = { x: 50, y: 5 }; // near bottom (y=0 is bottom in grip space)
    const result = applyStandoff(point, grip, dist);
    expect(result).toEqual({ x: 500, y: 420 });
  });

  it('returns the original point if grip is null/undefined', () => {
    expect(applyStandoff(point, null, dist)).toEqual(point);
    expect(applyStandoff(point, undefined, dist)).toEqual(point);
  });

  it('respects custom standoff distance', () => {
    const grip = { x: 5, y: 50 }; // left
    const result = applyStandoff({ x: 300, y: 300 }, grip, 50);
    expect(result.x).toBe(250);
    expect(result.y).toBe(300);
  });
});
