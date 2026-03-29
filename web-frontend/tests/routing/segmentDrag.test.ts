/**
 * tests/routing/segmentDrag.test.ts
 *
 * Unit tests for src/utils/pathfinding/segmentDrag.ts
 *
 * Covers (Rigid Rod Kinematics):
 *  1. snap() — grid snapping
 *  2. findSegmentIndex() — locating a segment within a path
 *  3. moveSegment() — rigid rod drag assertions:
 *       a. Vertical segment drag: Y coordinates LOCKED, only X changes
 *       b. Horizontal segment drag: X coordinates LOCKED, only Y changes
 *       c. Path remains orthogonal after drag
 *       d. Adjacent segments are re-connected correctly
 *       e. Edge cases (boundary indices, zero-delta)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { snap, moveSegment, findSegmentIndex } from '@/utils/pathfinding/segmentDrag';
import type { Point } from '@/utils/pathfinding/types';

// ──────────────────────────────────────────────────────────
// Helper utilities
// ──────────────────────────────────────────────────────────

/** Assert every adjacent pair in path is orthogonal */
function assertOrthogonal(path: Point[], label = '') {
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const ok = Math.abs(a.x - b.x) < 0.001 || Math.abs(a.y - b.y) < 0.001;
    expect(ok, `${label} diagonal at [${a.x},${a.y}]→[${b.x},${b.y}]`).toBe(true);
  }
}

// ──────────────────────────────────────────────────────────
// 1. snap()
// ──────────────────────────────────────────────────────────
describe('snap', () => {
  it('snaps to nearest 10px grid by default', () => {
    expect(snap(14)).toBe(10);
    expect(snap(15)).toBe(20);
    expect(snap(0)).toBe(0);
    expect(snap(100)).toBe(100);
  });

  it('snaps to a custom grid size', () => {
    expect(snap(23, 5)).toBe(25);
    expect(snap(22, 5)).toBe(20);
    expect(snap(50, 25)).toBe(50);
    expect(snap(37, 25)).toBe(25);
  });

  it('handles negative values', () => {
    expect(snap(-14)).toBe(-10);
    // JS Math.round rounds "half" toward +infinity: Math.round(-1.5) === -1
    // So snap(-15) = Math.round(-1.5) * 10 = -1 * 10 = -10
    expect(snap(-15)).toBe(-10);
    // But snap(-16) = Math.round(-1.6) * 10 = -2 * 10 = -20
    expect(snap(-16)).toBe(-20);
  });
});

// ──────────────────────────────────────────────────────────
// 2. findSegmentIndex()
// ──────────────────────────────────────────────────────────
describe('findSegmentIndex', () => {
  /**
   * Test path:  A─B─C─D (horizontal, vertical, horizontal)
   *   A = (100, 200)
   *   B = (100, 400)   ← vertical segment A→B
   *   C = (500, 400)   ← horizontal segment B→C
   *   D = (500, 600)   ← vertical segment C→D
   */
  const path: Point[] = [
    { x: 100, y: 200 },
    { x: 100, y: 400 },
    { x: 500, y: 400 },
    { x: 500, y: 600 },
  ];

  it('finds segment index 0 (A→B vertical)', () => {
    expect(findSegmentIndex(path, { x: 100, y: 200 }, { x: 100, y: 400 })).toBe(0);
  });

  it('finds segment index 1 (B→C horizontal)', () => {
    expect(findSegmentIndex(path, { x: 100, y: 400 }, { x: 500, y: 400 })).toBe(1);
  });

  it('finds segment index 2 (C→D vertical)', () => {
    expect(findSegmentIndex(path, { x: 500, y: 400 }, { x: 500, y: 600 })).toBe(2);
  });

  it('returns -1 when no segment matches', () => {
    expect(findSegmentIndex(path, { x: 999, y: 999 }, { x: 888, y: 888 })).toBe(-1);
  });

  it('matches within the default tolerance of 4px', () => {
    // Points 3px off the actual path points
    expect(findSegmentIndex(path, { x: 103, y: 203 }, { x: 103, y: 403 })).toBe(0);
  });

  it('does NOT match when delta exceeds tolerance', () => {
    // Points 10px off — outside 4px default tolerance
    expect(findSegmentIndex(path, { x: 110, y: 210 }, { x: 110, y: 410 })).toBe(-1);
  });
});

// ──────────────────────────────────────────────────────────
// 3. moveSegment() — Rigid Rod Kinematics
// ──────────────────────────────────────────────────────────
describe('moveSegment — rigid rod kinematics', () => {
  /**
   * Reference path (Z-shape): start → horizontal → vertical → horizontal → end
   *
   *   P0 = (100, 200)
   *   P1 = (400, 200)   ← segment 0: horizontal (P0→P1)
   *   P2 = (400, 600)   ← segment 1: vertical   (P1→P2)  ← THIS IS THE DRAG TARGET
   *   P3 = (700, 600)   ← segment 2: horizontal (P2→P3)
   *   P4 = (700, 800)   ← segment 3: vertical   (P3→P4)
   */
  const basePath: Point[] = [
    { x: 100, y: 200 },
    { x: 400, y: 200 },
    { x: 400, y: 600 },
    { x: 700, y: 600 },
    { x: 700, y: 800 },
  ];

  // ────── 3a: Vertical segment drag — Y coords LOCKED ──────
  describe('dragging a VERTICAL segment horizontally (Rigid Rod)', () => {
    const verticalSegIndex = 1; // P1→P2 (both at x=400)
    const dx = 80; // drag right by 80px
    const dy = 0;

    let result: Point[];

    beforeEach(() => {
      result = moveSegment(basePath, verticalSegIndex, dx, dy);
    });

    it('shifts X of both segment endpoints by dx', () => {
      expect(result[1].x).toBe(400 + dx); // P1.x
      expect(result[2].x).toBe(400 + dx); // P2.x
    });

    it('LOCKS Y coordinates of both segment endpoints (rigid rod)', () => {
      // Y must remain unchanged — this is the core kinematics assertion
      expect(result[1].y).toBe(basePath[1].y); // P1.y = 200 unchanged
      expect(result[2].y).toBe(basePath[2].y); // P2.y = 600 unchanged
    });

    it('preserves min/max Y bounds across the whole path', () => {
      const Ys = result.map((p) => p.y);
      const minY = Math.min(...Ys);
      const maxY = Math.max(...Ys);
      const origYs = basePath.map((p) => p.y);
      expect(minY).toBe(Math.min(...origYs));
      expect(maxY).toBe(Math.max(...origYs));
    });

    it('path remains strictly orthogonal after drag', () => {
      assertOrthogonal(result, 'vertical-drag');
    });

    it('immutably returns a NEW array (does not mutate original)', () => {
      expect(result).not.toBe(basePath);
      expect(basePath[1].x).toBe(400); // original unchanged
    });

    it('handles leftward drag (negative dx)', () => {
      const left = moveSegment(basePath, verticalSegIndex, -50, 0);
      expect(left[1].x).toBe(350);
      expect(left[2].x).toBe(350);
      // Y still locked
      expect(left[1].y).toBe(200);
      expect(left[2].y).toBe(600);
    });
  });

  // ────── 3b: Horizontal segment drag — X coords LOCKED ──────
  describe('dragging a HORIZONTAL segment vertically (Rigid Rod)', () => {
    const horizontalSegIndex = 2; // P2→P3 (both at y=600)
    const dx = 0;
    const dy = -100; // drag up by 100px

    let result: Point[];

    beforeEach(() => {
      result = moveSegment(basePath, horizontalSegIndex, dx, dy);
    });

    it('shifts Y of both segment endpoints by dy', () => {
      expect(result[2].y).toBe(600 + dy); // P2.y
      expect(result[3].y).toBe(600 + dy); // P3.y
    });

    it('LOCKS X coordinates of both segment endpoints (rigid rod)', () => {
      expect(result[2].x).toBe(basePath[2].x); // P2.x = 400 unchanged
      expect(result[3].x).toBe(basePath[3].x); // P3.x = 700 unchanged
    });

    it('leaves X coordinates of ALL non-dragged points unchanged', () => {
      for (let i = 0; i < result.length; i++) {
        expect(result[i].x).toBe(basePath[i].x);
      }
    });

    it('path remains strictly orthogonal after drag', () => {
      assertOrthogonal(result, 'horizontal-drag');
    });

    it('handles downward drag (positive dy)', () => {
      const down = moveSegment(basePath, horizontalSegIndex, 0, 50);
      expect(down[2].y).toBe(650);
      expect(down[3].y).toBe(650);
      // X still locked
      expect(down[2].x).toBe(400);
      expect(down[3].x).toBe(700);
    });
  });

  // ────── 3c: Adjacent segment connectivity ──────
  describe('adjacent segment connectivity after drag', () => {
    it('the dragged segment stays connected to the previous point (P0→P1)', () => {
      // After moving vertical seg [1] right, P0 and new P1 share Y (horizontal link)
      const result = moveSegment(basePath, 1, 100, 0);
      // P0.y should equal P1.y for horizontal connectivity
      expect(result[0].y).toBe(result[1].y);
    });

    it('the dragged segment stays connected to the next point (P2→P3)', () => {
      // After moving vertical seg [1] right, new P2 and P3 share Y (horizontal link)
      const result = moveSegment(basePath, 1, 100, 0);
      expect(result[2].y).toBe(result[3].y);
    });

    it('dragging the first horizontal segment preserves P0', () => {
      // Path: P0→P1 horizontal (y=200), dragging dy=50
      const simplePath: Point[] = [
        { x: 100, y: 200 },
        { x: 500, y: 200 },
        { x: 500, y: 500 },
      ];
      const result = moveSegment(simplePath, 0, 0, 50);
      // The horizontal segment is seg index 0 (P0→P1)
      expect(result[0].y).toBe(250);
      expect(result[1].y).toBe(250);
      // Vertical segment P1→P2 remains — P2.y must stay at 500
      expect(result[2].y).toBe(500);
    });
  });

  // ────── 3d: Edge cases ──────
  describe('edge cases', () => {
    it('returns the original path unchanged for out-of-bounds index (negative)', () => {
      const result = moveSegment(basePath, -1, 50, 50);
      expect(result).toEqual(basePath);
    });

    it('returns the original path unchanged for out-of-bounds index (>= length-1)', () => {
      const result = moveSegment(basePath, basePath.length - 1, 50, 50);
      expect(result).toEqual(basePath);
    });

    it('returns an equivalent path (no visible change) when dx=0, dy=0', () => {
      const result = moveSegment(basePath, 1, 0, 0);
      expect(result).toEqual(basePath);
    });

    it('works on a minimal 2-point path', () => {
      const twoPoint: Point[] = [{ x: 0, y: 0 }, { x: 100, y: 0 }];
      // seg index 0 = horizontal, move dy=50
      const result = moveSegment(twoPoint, 0, 0, 50);
      expect(result[0].y).toBe(50);
      expect(result[1].y).toBe(50);
    });

    it('path length is preserved (no points added or removed)', () => {
      const result = moveSegment(basePath, 1, 80, 0);
      expect(result).toHaveLength(basePath.length);
    });
  });

  // ────── 3e: orthogonality after multiple drags ──────
  describe('orthogonality maintained through chained drags', () => {
    it('remains orthogonal after two sequential drags on different segments', () => {
      const step1 = moveSegment(basePath, 1, 60, 0);  // drag vertical right
      const step2 = moveSegment(step1, 2, 0, -40);    // then drag horizontal up
      assertOrthogonal(step2, 'chained-drag');
    });

    it('correctly locks Y/X after reversed drag direction', () => {
      // Drag vertical segment right, then drag it back left — should return near original Xs
      const step1 = moveSegment(basePath, 1, 80, 0);
      const step2 = moveSegment(step1, 1, -80, 0);
      // P1.x and P2.x should be back to original 400
      expect(step2[1].x).toBeCloseTo(400);
      expect(step2[2].x).toBeCloseTo(400);
      // Y coords always locked
      expect(step2[1].y).toBe(200);
      expect(step2[2].y).toBe(600);
    });
  });
});
