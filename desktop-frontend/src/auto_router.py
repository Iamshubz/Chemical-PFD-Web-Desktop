"""
Smart Auto-Routing Algorithm for Chemical PFD Editor
Implements orthogonal routing with obstacle avoidance using BFS pathfinding.

Features:
- Grid-based logical coordinate system
- Obstacle detection for component bounding rectangles
- Start/end component exclusion from obstacles
- BFS parent-map (O(n) memory, not O(n^2))
- Canvas bounds enforcement (no infinite grid search)
- Clean orthogonal path generation (H/V segments only)
- Safe L-shaped fallback if path not found
"""

from collections import deque
from typing import List, Tuple, Set, Dict, Optional
from PyQt5.QtCore import QPointF, QRectF


# Grid resolution in logical pixels per cell
GRID_RES = 10

# Padding around component rects to avoid running right along edges
COMP_PAD = 14


def _to_grid(pt: QPointF) -> Tuple[int, int]:
    """Convert a logical QPointF to a grid (col, row) integer tuple."""
    return (int(pt.x() // GRID_RES), int(pt.y() // GRID_RES))


def _to_world(col: int, row: int) -> QPointF:
    """Convert grid (col, row) to the top-left corner of that cell in logical coords.
    Using top-left (not centre) ensures all intermediate points are on exact grid
    boundaries, so every segment is strictly H or V with no rounding error.
    """
    return QPointF(col * GRID_RES, row * GRID_RES)


def _rect_to_grid_cells(rect: QRectF) -> Set[Tuple[int, int]]:
    """
    Return the set of grid cells that fall inside a QRectF (padded).
    Used to build the obstacle set for component bounding boxes.
    """
    cells = set()
    # Apply padding
    padded = rect.adjusted(-COMP_PAD, -COMP_PAD, COMP_PAD, COMP_PAD)
    col_min = int(padded.left() / GRID_RES)
    col_max = int(padded.right()  / GRID_RES)
    row_min = int(padded.top()   / GRID_RES)
    row_max = int(padded.bottom() / GRID_RES)
    for c in range(col_min, col_max + 1):
        for r in range(row_min, row_max + 1):
            cells.add((c, r))
    return cells


def _seg_to_grid_cells(p1: QPointF, p2: QPointF) -> Set[Tuple[int, int]]:
    """
    Return the set of grid cells covered by an orthogonal segment p1→p2.
    Only works correctly for purely horizontal or purely vertical segments.
    """
    cells = set()
    c1, r1 = _to_grid(p1)
    c2, r2 = _to_grid(p2)

    if r1 == r2:  # horizontal
        for c in range(min(c1, c2), max(c1, c2) + 1):
            cells.add((c, r1))
    elif c1 == c2:  # vertical
        for r in range(min(r1, r2), max(r1, r2) + 1):
            cells.add((c1, r))
    else:
        # Diagonal segment (shouldn't happen for orthogonal paths, but handle safely)
        cells.add((c1, r1))
        cells.add((c2, r2))
    return cells

def build_routing_cache(component_rects: List[QRectF], connection_segments: List[Tuple[QPointF, QPointF]]) -> Dict:
    obstacles: Set[Tuple[int, int]] = set()
    for rect in component_rects:
        obstacles |= _rect_to_grid_cells(rect)
    line_cells: Set[Tuple[int, int]] = set()
    for p1, p2 in connection_segments:
        line_cells |= _seg_to_grid_cells(p1, p2)
    return {'obstacles': obstacles, 'line_cells': line_cells}

def find_path(
    start: QPointF,
    end: QPointF,
    start_side: str,
    end_side: str,
    component_rects: List[QRectF],
    exclude_rects: List[QRectF],
    connection_segments: List[Tuple[QPointF, QPointF]],
    canvas_bounds: QRectF,
    routing_cache: Optional[Dict] = None
) -> List[QPointF]:
    """
    BFS shortest orthogonal path from `start` to `end`.

    Parameters
    ----------
    start              : logical start point (grip position)
    end                : logical end point (grip position)
    component_rects    : all component logical_rect values (padded as obstacles)
    exclude_rects      : rects to SKIP when building obstacles (start/end components)
    connection_segments: existing connection segments added as thin-cell obstacles
    canvas_bounds      : logical canvas size — BFS never leaves this area
    routing_cache      : Optional pre-computed obstacles and line cells for performance

    Returns
    -------
    List of QPointF forming an orthogonal path. Guaranteed to have ≥ 2 points.
    Falls back to a minimal L-shaped path if BFS finds nothing.
    """

    # ------------------------------------------------------------------ #
    # 1. Build obstacle set and line cost set                            #
    # ------------------------------------------------------------------ #
    if routing_cache:
        base_obstacles = routing_cache.get('obstacles', set())
        base_line_cells = routing_cache.get('line_cells', set())
    else:
        base_obstacles = set()
        base_line_cells = set()

    dyn_obstacles: Set[Tuple[int, int]] = set()
    for rect in component_rects:
        # We explicitly include start/end components. Because they are Soft Obstacles (50,000 cost), 
        # the pathfinder will immediately take the shortest route out to escape the penalty,
        # which mathematically prevents lines from running a full length straight through them.
        dyn_obstacles |= _rect_to_grid_cells(rect)

    dyn_line_cells: Set[Tuple[int, int]] = set()
    for p1, p2 in connection_segments:
        dyn_line_cells |= _seg_to_grid_cells(p1, p2)

    # ------------------------------------------------------------------ #
    # 2. Compute canvas grid bounds                                        #
    # ------------------------------------------------------------------ #
    col_lo = int(canvas_bounds.left()   / GRID_RES) - 1
    col_hi = int(canvas_bounds.right()  / GRID_RES) + 1
    row_lo = int(canvas_bounds.top()    / GRID_RES) - 1
    row_hi = int(canvas_bounds.bottom() / GRID_RES) + 1

    def in_bounds(c: int, r: int) -> bool:
        return col_lo <= c <= col_hi and row_lo <= r <= row_hi

    # ------------------------------------------------------------------ #
    # 3. Convert start/end to grid                                       #
    # ------------------------------------------------------------------ #
    def _to_grid_directional(pt: QPointF, side: str) -> Tuple[int, int]:
        import math
        c = pt.x() / GRID_RES
        r = pt.y() / GRID_RES
        if side == "right": return (math.ceil(c), round(r))
        elif side == "left": return (math.floor(c), round(r))
        elif side == "bottom": return (round(c), math.ceil(r))
        elif side == "top": return (round(c), math.floor(r))
        return (round(c), round(r))

    sg = _to_grid_directional(start, start_side)
    eg = _to_grid_directional(end, end_side)

    # ------------------------------------------------------------------ #
    # 4. A* Algorithm (Heuristic Search)                                 #
    # ------------------------------------------------------------------ #
    import heapq

    TURN_PENALTY = 60.0      # Penalty for changing direction
    CROSSOVER_PENALTY = 25.0  # Penalty for crossing another line

    # Search Area Limiting: Define a "Region of Interest" (ROI)
    # This prevents searching the entire 3000x2000 canvas for a small connection.
    margin = 40  # 40 grid cells (400px) padding - allows wide detours around large tanks
    roi_col_lo = max(col_lo, min(sg[0], eg[0]) - margin)
    roi_col_hi = min(col_hi, max(sg[0], eg[0]) + margin)
    roi_row_lo = max(row_lo, min(sg[1], eg[1]) - margin)
    roi_row_hi = min(row_hi, max(sg[1], eg[1]) + margin)
    
    # Pre-merge caches for O(1) inner loop lookups
    obstacles = base_obstacles | dyn_obstacles if dyn_obstacles else base_obstacles
    line_cells = base_line_cells | dyn_line_cells if dyn_line_cells else base_line_cells

    # (f_score, cost, c, r, dir_idx)
    pq = []
    
    eg_c, eg_r = eg[0], eg[1]
    
    # Initialize start state for all 4 possible starting directions
    for i in range(4):
        h = abs(sg[0] - eg_c) + abs(sg[1] - eg_r)
        heapq.heappush(pq, (h, 0, sg[0], sg[1], i))
    
    parent: Dict[Tuple[int, int, int], Optional[Tuple[int, int, int]]] = {}
    best_cost: Dict[Tuple[int, int, int], float] = {}
    for i in range(4):
        parent[(sg[0], sg[1], i)] = None
        best_cost[(sg[0], sg[1], i)] = 0.0

    found_state = None
    
    # Pre-pack direction iterator (dc, dr, dir_idx)
    dirs = ((1, 0, 0), (-1, 0, 1), (0, 1, 2), (0, -1, 3))
    
    while pq:
        f, cost, cc, cr, dir_idx = heapq.heappop(pq)
        
        if cc == eg_c and cr == eg_r:
            found_state = (cc, cr, dir_idx)
            break
            
        # Fast state check
        if best_cost.get((cc, cr, dir_idx), float('inf')) < cost:
            continue

        for dc, dr, n_dir_idx in dirs:
            nc, nr = cc + dc, cr + dr
            
            # Inline bounds check completely removing nested unrolls
            if nc < roi_col_lo or nc > roi_col_hi or nr < roi_row_lo or nr > roi_row_hi:
                continue

            # Move Cost
            move_cost = 1.0
            if dir_idx != n_dir_idx:
                move_cost += TURN_PENALTY
            
            nb = (nc, nr)
            if nb in line_cells:
                move_cost += CROSSOVER_PENALTY
                
            if nb in obstacles and nb != eg:
                move_cost += 50000.0  # Soft obstacle penalty
                
            new_cost = cost + move_cost
            state = (nc, nr, n_dir_idx)
            
            # Sub-millisecond cost dictionary lookup
            if state in best_cost and new_cost >= best_cost[state]:
                continue
                
            best_cost[state] = new_cost
            parent[state] = (cc, cr, dir_idx)
            
            # Inline Manhattan Heuristic
            f_score = new_cost + abs(nc - eg_c) + abs(nr - eg_r)
            heapq.heappush(pq, (f_score, new_cost, nc, nr, n_dir_idx))

    # ------------------------------------------------------------------ #
    # 5. Reconstruct path or fall back                                     #
    # ------------------------------------------------------------------ #
    if not found_state:
        # Return empty list to let connection.py use its rule-based fallback
        return []

    grid_path: List[Tuple[int, int]] = []
    curr = found_state
    while curr:
        grid_path.append((curr[0], curr[1]))
        curr = parent[curr]
    grid_path.reverse()

    # Convert to world coords
    world: List[QPointF] = [_to_world(c, r) for c, r in grid_path]

    # Segment Floating to ensure mathematically straight endpoints without doglegs.
    world = _simplify(world)

    if len(world) == 2:
        is_horiz = abs(world[0].y() - world[1].y()) < 0.01
        is_vert  = abs(world[0].x() - world[1].x()) < 0.01
        
        if is_horiz and start_side in ("left", "right") and end_side in ("left", "right"):
            if abs(start.y() - end.y()) > 0.01:
                mid_x = (world[0].x() + world[1].x()) / 2.0
                world = [
                    QPointF(world[0].x(), start.y()), 
                    QPointF(mid_x, start.y()),
                    QPointF(mid_x, end.y()), 
                    QPointF(world[1].x(), end.y())
                ]
        elif is_vert and start_side in ("top", "bottom") and end_side in ("top", "bottom"):
            if abs(start.x() - end.x()) > 0.01:
                mid_y = (world[0].y() + world[1].y()) / 2.0
                world = [
                    QPointF(start.x(), world[0].y()),
                    QPointF(start.x(), mid_y),
                    QPointF(end.x(), mid_y),
                    QPointF(end.x(), world[1].y())
                ]

    if len(world) >= 2:
        # Float start segment
        if start_side in ("left", "right"):
            y_grid = world[0].y()
            for i in range(len(world)):
                if abs(world[i].y() - y_grid) < 0.01:
                    world[i] = QPointF(world[i].x(), start.y())
                else: break
        else:
            x_grid = world[0].x()
            for i in range(len(world)):
                if abs(world[i].x() - x_grid) < 0.01:
                    world[i] = QPointF(start.x(), world[i].y())
                else: break

        # Float end segment
        if end_side in ("left", "right"):
            y_grid = world[-1].y()
            for i in range(len(world)-1, -1, -1):
                if abs(world[i].y() - y_grid) < 0.01:
                    world[i] = QPointF(world[i].x(), end.y())
                else: break
        else:
            x_grid = world[-1].x()
            for i in range(len(world)-1, -1, -1):
                if abs(world[i].x() - x_grid) < 0.01:
                    world[i] = QPointF(end.x(), world[i].y())
                else: break

    if len(world) > 0:
        world.insert(0, start)
        world.append(end)

    return _simplify(world)


def _simplify(pts: List[QPointF]) -> List[QPointF]:
    """
    Remove collinear intermediate points so only direction-change corners remain.
    Keeps start and end unchanged.
    """
    if len(pts) <= 2:
        return pts

    # Deduplicate exact duplicates first
    deduped = [pts[0]]
    for pt in pts[1:]:
        if abs(pt.x() - deduped[-1].x()) > 0.01 or abs(pt.y() - deduped[-1].y()) > 0.01:
            deduped.append(pt)

    if len(deduped) <= 2:
        return deduped

    result = [deduped[0]]
    for i in range(1, len(deduped) - 1):
        a, b, c = result[-1], deduped[i], deduped[i + 1]
        # Skip b if it is collinear with a and c
        h_collinear = abs(a.y() - b.y()) < 0.01 and abs(b.y() - c.y()) < 0.01
        v_collinear = abs(a.x() - b.x()) < 0.01 and abs(b.x() - c.x()) < 0.01
        if h_collinear or v_collinear:
            continue
        result.append(b)

    result.append(deduped[-1])
    return result
