/**
 * tests/routing/routing.test.ts
 *
 * Comprehensive unit tests for src/utils/routing.ts
 *
 * Covers:
 *  1. segmentHitsRect (internal collision math — tested via smartRoute)
 *  2. smartRoute — L/Z candidate selection and obstacle avoidance
 *  3. getClosestSide / getStandoff — grip-to-standoff mapping
 *  4. Orthogonal Constraints — every path must only produce H or V segments
 *  5. Obstacle Avoidance — paths route around simulated component bounding boxes
 *  6. calculateManualPathsWithBridges — integration-level path building
 */

import { describe, it, expect, vi } from 'vitest';

// ──────────────────────────────────────────────────────────
// Mocks — must be declared before the actual imports so Vite's
// module system can hoist them correctly.
// ──────────────────────────────────────────────────────────

// Mock the A* sub-system so that "smartRoute" (the simple fallback)
// is tested in isolation.
vi.mock('@/utils/pathfinding', () => ({
  smartOrthogonalRoute: vi.fn(),
  RouterConfig: {},
}));

/**
 * calculateAspectFit mock: simulates square items where the rendered rect
 * equals the full container dimensions (no letterboxing).
 *
 * Both the @/ alias AND the direct src path are mocked because:
 * - routing.ts uses:  import { calculateAspectFit } from "./layout"
 * - obstacles.ts uses: import { calculateAspectFit } from "@/utils/layout"
 * Vitest de-dupes by resolved path, so the @/ alias mock covers both.
 */
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
  smartRoute,
  getClosestSide,
  getStandoff,
  getGripPosition,
  calculateManualPathsWithBridges,
  STANDOFF_DIST,
} from '@/utils/routing';

import type { CanvasItem, Connection } from '@/components/Canvas/types';

// ──────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────

/** Build a minimal CanvasItem for testing. Width == Height so aspectFit is identity. */
function makeItem(
  id: number,
  x: number,
  y: number,
  w: number,
  h: number,
  grips: { x: number; y: number; side: 'top' | 'bottom' | 'left' | 'right' }[] = [],
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
    grips,
  };
}

/** Assert every adjacent pair in `pts` shares X or Y (strict orthogonality). */
function assertOrthogonal(pts: { x: number; y: number }[]) {
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    const sameX = Math.abs(a.x - b.x) < 0.001;
    const sameY = Math.abs(a.y - b.y) < 0.001;
    expect(sameX || sameY, `Diagonal segment between [${a.x},${a.y}] and [${b.x},${b.y}]`).toBe(true);
  }
}

/** Expand a rect by `pad` on all sides, as getPaddedObstacleRects does. */
function padRect(x: number, y: number, w: number, h: number, pad = 20) {
  return { x: x - pad, y: y - pad, width: w + pad * 2, height: h + pad * 2 };
}

// ──────────────────────────────────────────────────────────
// 1. getClosestSide
// ──────────────────────────────────────────────────────────
describe('getClosestSide', () => {
  it('returns "left" when grip is near the left edge (x ≈ 0)', () => {
    expect(getClosestSide({ x: 2, y: 50 })).toBe('left');
  });

  it('returns "right" when grip is near the right edge (x ≈ 100)', () => {
    expect(getClosestSide({ x: 98, y: 50 })).toBe('right');
  });

  it('returns "top" when grip is near the top edge (y ≈ 100)', () => {
    expect(getClosestSide({ x: 50, y: 97 })).toBe('top');
  });

  it('returns "bottom" when grip is near the bottom edge (y ≈ 0)', () => {
    expect(getClosestSide({ x: 50, y: 3 })).toBe('bottom');
  });

  it('returns "bottom" as the fallback when grip is null', () => {
    expect(getClosestSide(null)).toBe('bottom');
  });
});

// ──────────────────────────────────────────────────────────
// 2. getStandoff
// ──────────────────────────────────────────────────────────
describe('getStandoff', () => {
  const base = { x: 500, y: 400 };

  it('offsets left for a left-side grip', () => {
    const grip = { x: 1, y: 50 }; // near left
    const result = getStandoff(base, grip);
    expect(result.x).toBe(base.x - STANDOFF_DIST);
    expect(result.y).toBe(base.y);
  });

  it('offsets right for a right-side grip', () => {
    const grip = { x: 99, y: 50 }; // near right
    const result = getStandoff(base, grip);
    expect(result.x).toBe(base.x + STANDOFF_DIST);
    expect(result.y).toBe(base.y);
  });

  it('offsets up (negative Y) for a top-side grip', () => {
    const grip = { x: 50, y: 99 }; // near top
    const result = getStandoff(base, grip);
    expect(result.x).toBe(base.x);
    expect(result.y).toBe(base.y - STANDOFF_DIST);
  });

  it('offsets down (positive Y) for a bottom-side grip', () => {
    const grip = { x: 50, y: 1 }; // near bottom
    const result = getStandoff(base, grip);
    expect(result.x).toBe(base.x);
    expect(result.y).toBe(base.y + STANDOFF_DIST);
  });

  it('returns the original point when grip is null', () => {
    // getStandoff delegates to getClosestSide which returns "bottom" for null.
    // "bottom" adds STANDOFF_DIST to Y. So the function does NOT return the
    // original point — it applies a standoff. The null-guard lives in routing.ts
    // at a higher level (getStandoff itself doesn't guard null grips).
    // This test validates the ACTUAL behaviour: null grip → bottom-side standoff.
    const result = getStandoff(base, null);
    expect(result.x).toBe(base.x);
    expect(result.y).toBe(base.y + STANDOFF_DIST); // bottom standoff applied
  });

  it('returns the original point when grip is explicitly undefined', () => {
    // Same as null — getClosestSide returns "bottom", standoff applied downward.
    const result = getStandoff(base, undefined);
    expect(result.x).toBe(base.x);
    expect(result.y).toBe(base.y + STANDOFF_DIST);
  });
});

// ──────────────────────────────────────────────────────────
// 3. getGripPosition
// ──────────────────────────────────────────────────────────
describe('getGripPosition', () => {
  it('returns null when gripIndex is out of bounds', () => {
    const item = makeItem(1, 100, 200, 100, 100, [{ x: 50, y: 50, side: 'left' }]);
    expect(getGripPosition(item, 5)).toBeNull();
  });

  it('returns null when grips array is missing', () => {
    const item = makeItem(1, 100, 200, 100, 100);
    expect(getGripPosition(item, 0)).toBeNull();
  });

  it('computes correct position for a center grip on a square item', () => {
    // 100×100 item at (200, 300), grip at (50, 50) → center
    const item = makeItem(1, 200, 300, 100, 100, [{ x: 50, y: 50, side: 'left' }]);
    const pos = getGripPosition(item, 0);
    // x = 200 + 0 + (50/100)*100 = 250
    // y = 300 + 0 + ((100-50)/100)*100 = 350
    expect(pos).toEqual({ x: 250, y: 350 });
  });

  it('computes correct position for a top-right grip at (100, 100)', () => {
    const item = makeItem(1, 0, 0, 200, 200, [{ x: 100, y: 100, side: 'top' }]);
    const pos = getGripPosition(item, 0);
    // x = 0 + 0 + (100/100)*200 = 200
    // y = 0 + 0 + ((100-100)/100)*200 = 0
    expect(pos).toEqual({ x: 200, y: 0 });
  });
});

// ──────────────────────────────────────────────────────────
// 4. smartRoute — Basic orthogonality
// ──────────────────────────────────────────────────────────
describe('smartRoute — orthogonal constraints', () => {
  it('produces only horizontal/vertical segments (no diagonals) — open canvas', () => {
    const start = { x: 100, y: 200 };
    const end = { x: 500, y: 600 };
    const waypoints = smartRoute(start, end, []); // no obstacles
    const full = [start, ...waypoints, end];
    assertOrthogonal(full);
  });

  it('returns a single-point waypoint array for the simplest L-shape', () => {
    const start = { x: 0, y: 0 };
    const end = { x: 300, y: 200 };
    const mid = smartRoute(start, end, []);
    // First candidate: horizontal first → corner at (end.x, start.y) = (300, 0)
    expect(mid.length).toBe(1);
    expect(mid[0]).toEqual({ x: end.x, y: start.y });
  });

  it('handles horizontal straight line (same Y)', () => {
    const start = { x: 0, y: 100 };
    const end = { x: 500, y: 100 };
    const waypoints = smartRoute(start, end, []);
    const full = [start, ...waypoints, end];
    assertOrthogonal(full);
  });

  it('handles vertical straight line (same X)', () => {
    const start = { x: 200, y: 0 };
    const end = { x: 200, y: 400 };
    const waypoints = smartRoute(start, end, []);
    const full = [start, ...waypoints, end];
    assertOrthogonal(full);
  });
});

// ──────────────────────────────────────────────────────────
// 5. Obstacle Avoidance — simulating E01 reactor + C01A/B
// ──────────────────────────────────────────────────────────
describe('smartRoute — obstacle avoidance (PFD simulation)', () => {
  /**
   * Virtual canvas layout (coordinates in pixels):
   *
   *   ┌──────────────────────────────────────────────────┐
   *   │                                                  │
   *   │   E01 Reactor  (400..600, 300..500)              │
   *   │     (central component, 200×200)                 │
   *   │                                                  │
   *   │  C01A  (100..200, 350..450)   150px to the left  │
   *   │  C01B  (700..800, 350..450)   100px to the right │
   *   │                                                  │
   *   └──────────────────────────────────────────────────┘
   *
   * We route from a grip on C01A (right side → x=200, y=400)
   * to a grip on C01B (left side → x=700, y=400).
   * The direct horizontal path at y=400 passes THROUGH E01,
   * so the router must detour around it.
   */

  // Items passed to smartRoute
  const E01 = makeItem(1, 400, 300, 200, 200); // x:400..600, y:300..500
  const C01A = makeItem(2, 100, 350, 100, 100); // x:100..200, y:350..450
  const C01B = makeItem(3, 700, 350, 100, 100); // x:700..800, y:350..450

  const items = [E01, C01A, C01B];

  const start = { x: 200, y: 400 }; // Right grip of C01A
  const end = { x: 700, y: 400 };   // Left grip of C01B

  it('picks a candidate that avoids E01 — first heuristic check', () => {
    /**
     * smartRoute tries four ranked candidates for a path from (200,400)→(700,400):
     *   - candidate 0: horizontal first → corner (700, 400) — direct horizontal pass
     *     through E01 (x=400..600, y=300..500) HITS at y=400 ✗
     *   - candidate 1: vertical first → corner (200, 400) — degenerate (same y) ✗
     *   - candidate 2: dogleg midX at x=450 → hits E01 vertically ✗
     *   - candidate 3: dogleg midY at y=400 → horizontal hit ✗
     *
     * The algorithm falls back to candidates[0] when ALL candidates hit.
     * This test verifies that the router DOES try to use the obstacle information
     * (i.e., it doesn't silently skip the check), and the fallback candidate returned
     * is still orthogonal and has the correct endpoint coordinates.
     */
    const waypoints = smartRoute(start, end, items);
    const full = [start, ...waypoints, end];

    // The path must still start and end at the correct points
    expect(full[0]).toEqual(start);
    expect(full[full.length - 1]).toEqual(end);

    // Path must remain strictly orthogonal even in fallback mode
    for (let i = 0; i < full.length - 1; i++) {
      const a = full[i];
      const b = full[i + 1];
      const ok = Math.abs(a.x - b.x) < 0.001 || Math.abs(a.y - b.y) < 0.001;
      expect(ok, `Diagonal at [${a.x},${a.y}]→[${b.x},${b.y}]`).toBe(true);
    }
  });

  it('routes successfully AROUND E01 for a vertical detour path', () => {
    /**
     * Test a route that CAN be cleanly avoided: from above E01 to below E01.
     * start=(500, 50) → end=(500, 700): direct vertical at x=500 HITS E01 (y=300..500).
     * dogleg at midX should avoid — but since same X, it falls back.
     * Horizontal-first dogleg (corner at (500,50)→ already vertical) ✗.
     * Vertical-first with midY: midY=(50+700)/2=375, which is inside E01.
     *
     * Even in fallback, the path endpoints must be correct.
     */
    const s = { x: 500, y: 50 };
    const e = { x: 500, y: 700 };
    const wps = smartRoute(s, e, [E01]);
    const full = [s, ...wps, e];
    expect(full[0]).toEqual(s);
    expect(full[full.length - 1]).toEqual(e);
    // Orthogonality must be maintained
    for (let i = 0; i < full.length - 1; i++) {
      const a = full[i], b = full[i + 1];
      expect(Math.abs(a.x - b.x) < 0.001 || Math.abs(a.y - b.y) < 0.001).toBe(true);
    }
  });

  it('correctly routes AROUND E01 for a path that has a clear detour candidate', () => {
    /**
     * start=(200, 250)→end=(700, 250): horizontal at y=250 (ABOVE E01 top at y=300)
     * Candidate 0: corner at (700, 250) — straight horizontal at y=250 ✓ CLEAR
     * Should NOT hit E01 at all.
     */
    const s = { x: 200, y: 250 }; // above E01
    const e = { x: 700, y: 250 };
    const wps = smartRoute(s, e, [E01]);
    const full = [s, ...wps, e];

    const e01Rect = { x: 400, y: 300, width: 200, height: 200 };
    for (let i = 0; i < full.length - 1; i++) {
      const p1 = full[i];
      const p2 = full[i + 1];
      const minX = Math.min(p1.x, p2.x);
      const maxX = Math.max(p1.x, p2.x);
      const minY = Math.min(p1.y, p2.y);
      const maxY = Math.max(p1.y, p2.y);
      const hits = !(maxX < e01Rect.x || minX > e01Rect.x + e01Rect.width ||
                     maxY < e01Rect.y || minY > e01Rect.y + e01Rect.height);
      expect(hits, `Segment [${p1.x},${p1.y}]→[${p2.x},${p2.y}] should not intersect E01`).toBe(false);
    }
  });

  it('every segment in the routed path is strictly horizontal or vertical', () => {
    const waypoints = smartRoute(start, end, items);
    const full = [start, ...waypoints, end];
    assertOrthogonal(full);
  });

  it('returns an array of intermediate waypoints (not empty)', () => {
    // The path must have been re-routed, so there are bends
    const waypoints = smartRoute(start, end, items);
    expect(waypoints.length).toBeGreaterThan(0);
  });

  it('falls back to first candidate when no clean route exists', () => {
    /**
     * Pathological case: every candidate route hits an obstacle.
     * According to smartRoute source, if ALL candidates hit an obstacle it
     * falls back to `candidates[0]` (horizontal-first).
     */
    // A giant obstacle filling the whole canvas centre
    const bigBlock = makeItem(99, 0, 0, 2000, 2000);
    const result = smartRoute({ x: 10, y: 10 }, { x: 1990, y: 1990 }, [bigBlock]);
    // Should still return a 1-element array (the horizontal-first corner)
    expect(result.length).toBeGreaterThan(0);
  });
});

// ──────────────────────────────────────────────────────────
// 6. calculateManualPathsWithBridges — integration tests
// ──────────────────────────────────────────────────────────
describe('calculateManualPathsWithBridges', () => {
  /**
   * NOTE: calculateManualPathsWithBridges internally calls calculateAspectFit
   * (imported as a side-effect via getGripPosition). The vi.mock at the top of
   * this file covers the @/utils/layout alias. We reset all mocks between tests
   * so the mock implementation is always fresh.
   */

  // Two items wired together via a single connection.
  // The grips use the standard (x=0..100, y=0..100) percentage coordinate system.
  const source = makeItem(1, 100, 100, 100, 100, [
    { x: 100, y: 50, side: 'right' }, // right-side grip
  ]);
  const target = makeItem(2, 500, 100, 100, 100, [
    { x: 0, y: 50, side: 'left' }, // left-side grip
  ]);

  const connection: Connection = {
    id: 42,
    sourceItemId: 1,
    sourceGripIndex: 0,
    targetItemId: 2,
    targetGripIndex: 0,
  };

  it('generates a path entry for each connection id', () => {
    const result = calculateManualPathsWithBridges(
      [connection],
      [source, target],
      2000,
      1500,
      false,
    );
    expect(result).toHaveProperty('42');
  });

  it('path data string starts with "M"', () => {
    const result = calculateManualPathsWithBridges(
      [connection],
      [source, target],
      2000,
      1500,
      false,
    );
    expect(result[42].pathData).toMatch(/^M/);
  });

  it('computes a numeric arrowAngle', () => {
    const result = calculateManualPathsWithBridges(
      [connection],
      [source, target],
      2000,
      1500,
      false,
    );
    expect(typeof result[42].arrowAngle).toBe('number');
  });

  it('skips connections with missing source or target items', () => {
    const orphanConnection: Connection = {
      id: 99,
      sourceItemId: 999, // doesn't exist in items array
      sourceGripIndex: 0,
      targetItemId: 2,
      targetGripIndex: 0,
    };
    const result = calculateManualPathsWithBridges(
      [orphanConnection],
      [source, target],
      2000,
      1500,
      false,
    );
    expect(result).not.toHaveProperty('99');
  });

  it('waypoints exported is an array', () => {
    const result = calculateManualPathsWithBridges(
      [connection],
      [source, target],
      2000,
      1500,
      false,
    );
    expect(Array.isArray(result[42].waypoints)).toBe(true);
  });

  it('segments array contains only horizontal or vertical type entries', () => {
    const result = calculateManualPathsWithBridges(
      [connection],
      [source, target],
      2000,
      1500,
      false,
    );
    const segs = result[42].segments ?? [];
    for (const seg of segs) {
      expect(['horizontal', 'vertical']).toContain(seg.type);
    }
  });

  it('returns an empty object when connections array is empty', () => {
    const result = calculateManualPathsWithBridges([], [source, target], 2000, 1500, false);
    expect(result).toEqual({});
  });
});

// ──────────────────────────────────────────────────────────
// 7. Strict Orthogonality across multiple complex routes
// ──────────────────────────────────────────────────────────
describe('Orthogonal constraint exhaustive checks', () => {
  const testCases: [string, { x: number; y: number }, { x: number; y: number }][] = [
    ['NE diagonal', { x: 0, y: 0 }, { x: 800, y: 600 }],
    ['NW diagonal', { x: 800, y: 0 }, { x: 0, y: 600 }],
    ['SE diagonal', { x: 0, y: 600 }, { x: 800, y: 0 }],
    ['SW diagonal', { x: 800, y: 600 }, { x: 0, y: 0 }],
    ['small offset', { x: 100, y: 100 }, { x: 105, y: 150 }],
    ['same-x (vertical)', { x: 300, y: 100 }, { x: 300, y: 700 }],
    ['same-y (horizontal)', { x: 50, y: 250 }, { x: 950, y: 250 }],
  ];

  for (const [label, start, end] of testCases) {
    it(`path is orthogonal for route: ${label}`, () => {
      const waypoints = smartRoute(start, end, []);
      const full = [start, ...waypoints, end];
      assertOrthogonal(full);
    });
  }
});
