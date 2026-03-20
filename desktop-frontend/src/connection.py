from PyQt5.QtCore import QPoint, QPointF, QRectF, Qt, QLineF, QSizeF
from PyQt5.QtGui import QPainterPath, QColor, QPen, QBrush, QPolygonF
import math
from src.auto_router import AutoRouter

class Connection:
    GRIP_SIDE_TOLERANCE = 8.0
    OBSTACLE_CLEARANCE = 10.0

    def __init__(self, start_component, start_grip_index, start_side):
        self.start_component = start_component
        self.start_grip_index = start_grip_index
        self.start_side = start_side  # "top", "bottom", "left", "right"
        
        self.end_component = None
        self.end_grip_index = None
        self.end_side = None
        
        # New: Snap Target (Temporary during drag)
        self.snap_component = None 
        self.snap_grip_index = None
        self.snap_side = None

        self.current_pos = QPoint(0, 0) # Used during dragging
        self.path = [] # List of QPointF (Raw Orthogonal Points)
        self.painter_path = QPainterPath() # Final Path with Jumps

        
        # Interactive State
        self.is_selected = False
        self.path_offset = 0.0 # Moves the middle segment
        self.start_adjust = 0.0 # Moves the start stub (ns)
        self.end_adjust = 0.0 # Moves the end stub (pe)
        
        # Auto-Router Integration
        # NOTE: Auto-router temporarily disabled due to BFS pathfinding complexity
        # Using enhanced rule-based routing with orthogonality enforcement instead
        self.use_auto_router = False  # Disabled - using rule-based with orthogonal enforcement
        self.auto_router = AutoRouter(grid_resolution=10)  # Grid size: 10px

    def set_end_grip(self, component, grip_index, side):
        self.end_component = component
        self.end_grip_index = grip_index
        self.end_side = side

    def set_snap_target(self, component, grip_index, side):
        self.snap_component = component
        self.snap_grip_index = grip_index
        self.snap_side = side

    def clear_snap_target(self):
        self.snap_component = None
        self.snap_grip_index = None
        self.snap_side = None

    def get_start_pos(self):
        # canvas-relative coordinate (LOGICAL)
        if hasattr(self.start_component, "logical_rect"):
            return self.start_component.logical_rect.topLeft() + self.start_component.get_logical_grip_position(self.start_grip_index)
        # Fallback to visual (scaled) if logical not available? No, must trigger error or fallback safely.
        # But for now assume logical exists.
        return self.start_component.pos() + self.start_component.get_grip_position(self.start_grip_index)

    def get_end_pos(self):
        if self.end_component:
            return self.end_component.logical_rect.topLeft() + self.end_component.get_logical_grip_position(self.end_grip_index)
        
        # If snapping, return snap grip pos (Logical)
        if self.snap_component:
            return self.snap_component.logical_rect.topLeft() + self.snap_component.get_logical_grip_position(self.snap_grip_index)
            
        return self.current_pos
        
    def hit_test(self, pos: QPoint, tolerance=5.0):
        """Checks if the position is near the connection path.
        Returns the index of the first segment hit, or -1 if none.
        """
        if len(self.path) < 2:
            return -1
            
        for i in range(len(self.path) - 1):
            p1 = self.path[i]
            p2 = self.path[i+1]
            
            # Distance from point to line segment
            # Simplified for orthogonal lines
            if abs(p1.x() - p2.x()) < 1.0: # Vertical segment
                min_y = min(p1.y(), p2.y())
                max_y = max(p1.y(), p2.y())
                if min_y - tolerance <= pos.y() <= max_y + tolerance:
                    if abs(pos.x() - p1.x()) <= tolerance:
                        return i
            else: # Horizontal segment
                min_x = min(p1.x(), p2.x())
                max_x = max(p1.x(), p2.x())
                if min_x - tolerance <= pos.x() <= max_x + tolerance:
                    if abs(pos.y() - p1.y()) <= tolerance:
                        return i
        return -1

    # ------------------------------------------------------------------
    # PUBLIC ENTRY POINTS
    # ------------------------------------------------------------------

    def calculate_path(self, components=None, other_connections=None, use_auto_router=None):
        """Route this connection.  Always uses the clean orthogonal router."""
        self.path = []
        self.painter_path = QPainterPath()
        self._route(components or [])

    def enable_auto_router(self, enable: bool = True):
        """Legacy hook kept for call-site compatibility – always uses clean router."""
        self.use_auto_router = enable  # value ignored; kept for serialisation

    # ------------------------------------------------------------------
    # CLEAN ORTHOGONAL ROUTER
    # ------------------------------------------------------------------

    # Padding added around every obstacle rect
    _PAD = 14.0
    # Min stub length coming out of / going into a grip
    _STUB = 20.0

    def _route(self, components):
        """
        Produce a clean, minimal orthogonal path from start-grip to end-grip.

        Strategy
        --------
        1. Compute a stub point just outside the start and end grips.
        2. Try up to 4 candidate mid-points (horizontal-first, vertical-first,
           and two bypass routes above/below / left/right of the bounding box
           of all obstacles).
        3. For each candidate build a 3- or 5-point path, score it by counting
           how many obstacle rectangles it penetrates.
        4. Pick the cleanest (lowest score) candidate.  Among ties pick shortest.
        """
        S = QPointF(self.get_start_pos())
        E = QPointF(self.get_end_pos())

        start_side = self._resolve_grip_side(self.start_component, self.start_grip_index, self.start_side)
        target_side = self._resolve_target_side(S, E)

        stub = max(self._STUB, self._STUB + self.start_adjust)
        end_stub = max(self._STUB, self._STUB + self.end_adjust)

        # Point one stub-length out from each grip
        ns = self._stub_point(S, start_side, stub)
        pe = self._stub_point(E, target_side, end_stub)

        # Build obstacle rects (padded), excluding start/end/snap
        blocked = [
            comp.logical_rect.adjusted(-self._PAD, -self._PAD, self._PAD, self._PAD)
            for comp in components
            if hasattr(comp, "logical_rect")
            and comp not in (self.start_component, self.end_component, self.snap_component)
        ]

        # Candidate midpoints – try horizontal-first and vertical-first corners,
        # plus bypass rows/columns around all obstacles combined.
        candidates = self._candidate_paths(ns, pe, blocked)
        candidates.extend(self._expanded_fallback_candidates(ns, pe, blocked))

        # Hard rule: choose only paths that do not intersect any component.
        clear_candidates = [pts for pts in candidates if self._is_path_clear(pts, blocked)]
        if clear_candidates:
            best = min(clear_candidates, key=lambda pts: self._path_len(pts))
            self.path = self._dedup(best)
            return

        # Conservative fallback: if no clear route found, keep shortest-score path.
        best = min(candidates, key=lambda pts: (self._path_score(pts, blocked), self._path_len(pts)))
        self.path = self._dedup(best)

    def _stub_point(self, grip: QPointF, side: str, length: float) -> QPointF:
        if side == "right":  return QPointF(grip.x() + length, grip.y())
        if side == "left":   return QPointF(grip.x() - length, grip.y())
        if side == "top":    return QPointF(grip.x(), grip.y() - length)
        if side == "bottom": return QPointF(grip.x(), grip.y() + length)
        return QPointF(grip.x() + length, grip.y())

    def _candidate_paths(self, ns: QPointF, pe: QPointF, blocked: list) -> list:
        """Return a list of candidate point-lists, each a full orthogonal path
        from the start-grip through ns … pe to the end-grip."""
        S = QPointF(self.get_start_pos())
        E = QPointF(self.get_end_pos())
        off = self.path_offset

        paths = []

        # --- 3-segment: horizontal-first (corner at ns.x→pe.y then pe) ------
        # ns → (pe.x, ns.y) → pe
        c1 = QPointF(pe.x(), ns.y())
        paths.append([S, ns, c1, pe, E])

        # --- 3-segment: vertical-first (corner at ns.y→pe.x then pe) --------
        # ns → (ns.x, pe.y) → pe
        c2 = QPointF(ns.x(), pe.y())
        paths.append([S, ns, c2, pe, E])

        # --- 5-segment bypass: route via midpoint row/column -----------------
        if blocked:
            all_left   = min(r.left()   for r in blocked)
            all_right  = max(r.right()  for r in blocked)
            all_top    = min(r.top()    for r in blocked)
            all_bottom = max(r.bottom() for r in blocked)
        else:
            cx = (ns.x() + pe.x()) / 2
            cy = (ns.y() + pe.y()) / 2
            all_left = cx; all_right = cx; all_top = cy; all_bottom = cy

        gap = self._PAD + 6.0

        # bypass above all obstacles
        by_top = all_top - gap + off
        paths.append([S, ns,
                       QPointF(ns.x(), by_top),
                       QPointF(pe.x(), by_top),
                       pe, E])

        # bypass below all obstacles
        by_bot = all_bottom + gap + off
        paths.append([S, ns,
                       QPointF(ns.x(), by_bot),
                       QPointF(pe.x(), by_bot),
                       pe, E])

        # bypass left of all obstacles
        by_left = all_left - gap + off
        paths.append([S, ns,
                       QPointF(by_left, ns.y()),
                       QPointF(by_left, pe.y()),
                       pe, E])

        # bypass right of all obstacles
        by_right = all_right + gap + off
        paths.append([S, ns,
                       QPointF(by_right, ns.y()),
                       QPointF(by_right, pe.y()),
                       pe, E])

        return paths

    # ------------------------------------------------------------------
    # SCORING / GEOMETRY HELPERS
    # ------------------------------------------------------------------

    def _path_score(self, points: list, blocked: list) -> int:
        """Count how many (segment, obstacle) pairs intersect."""
        score = 0
        for i in range(len(points) - 1):
            for rect in blocked:
                if self._seg_hits_rect(points[i], points[i + 1], rect):
                    score += 1
        return score

    def _is_path_clear(self, points: list, blocked: list) -> bool:
        return self._path_score(points, blocked) == 0

    def _path_len(self, points: list) -> float:
        total = 0.0
        for i in range(len(points) - 1):
            total += abs(points[i+1].x()-points[i].x()) + abs(points[i+1].y()-points[i].y())
        return total

    def _expanded_fallback_candidates(self, ns: QPointF, pe: QPointF, blocked: list) -> list:
        """Create wider detours in case default candidates are blocked."""
        S = QPointF(self.get_start_pos())
        E = QPointF(self.get_end_pos())

        if blocked:
            all_left = min(r.left() for r in blocked)
            all_right = max(r.right() for r in blocked)
            all_top = min(r.top() for r in blocked)
            all_bottom = max(r.bottom() for r in blocked)
        else:
            all_left = min(ns.x(), pe.x())
            all_right = max(ns.x(), pe.x())
            all_top = min(ns.y(), pe.y())
            all_bottom = max(ns.y(), pe.y())

        gap = self._PAD + 36.0
        by_top = min(all_top, ns.y(), pe.y()) - gap
        by_bottom = max(all_bottom, ns.y(), pe.y()) + gap
        by_left = min(all_left, ns.x(), pe.x()) - gap
        by_right = max(all_right, ns.x(), pe.x()) + gap

        return [
            [S, ns, QPointF(ns.x(), by_top), QPointF(pe.x(), by_top), pe, E],
            [S, ns, QPointF(ns.x(), by_bottom), QPointF(pe.x(), by_bottom), pe, E],
            [S, ns, QPointF(by_left, ns.y()), QPointF(by_left, pe.y()), pe, E],
            [S, ns, QPointF(by_right, ns.y()), QPointF(by_right, pe.y()), pe, E],
        ]

    def _seg_hits_rect(self, p1: QPointF, p2: QPointF, rect: QRectF) -> bool:
        """Axis-aligned segment vs padded rect intersection."""
        if abs(p1.y() - p2.y()) < 0.5:          # horizontal
            y = p1.y()
            lo, hi = min(p1.x(), p2.x()), max(p1.x(), p2.x())
            return rect.top() < y < rect.bottom() and hi > rect.left() and lo < rect.right()
        if abs(p1.x() - p2.x()) < 0.5:           # vertical
            x = p1.x()
            lo, hi = min(p1.y(), p2.y()), max(p1.y(), p2.y())
            return rect.left() < x < rect.right() and hi > rect.top() and lo < rect.bottom()
        return False

    def _dedup(self, points: list) -> list:
        """Remove consecutive duplicate / collinear points."""
        if not points:
            return points
        out = [points[0]]
        for pt in points[1:]:
            if abs(pt.x() - out[-1].x()) > 0.05 or abs(pt.y() - out[-1].y()) > 0.05:
                out.append(pt)
        # Collapse collinear triples
        result = [out[0]]
        for i in range(1, len(out) - 1):
            a, b, c = result[-1], out[i], out[i+1]
            if abs(a.x()-b.x()) < 0.05 and abs(b.x()-c.x()) < 0.05:
                continue  # vertical collinear
            if abs(a.y()-b.y()) < 0.05 and abs(b.y()-c.y()) < 0.05:
                continue  # horizontal collinear
            result.append(b)
        if len(out) > 1:
            result.append(out[-1])
        return result

    # ------------------------------------------------------------------
    # SIDE-RESOLUTION HELPERS  (kept for _route / _candidate_paths)
    # ------------------------------------------------------------------

    def _resolve_grip_side(self, component, grip_index, fallback_side=None):
        if (
            component is None
            or grip_index is None
            or not hasattr(component, "logical_rect")
            or not hasattr(component, "get_logical_grip_position")
        ):
            return fallback_side or "right"

        local_pos = component.get_logical_grip_position(grip_index)
        rect = component.logical_rect
        distances = {
            "left":   abs(local_pos.x()),
            "right":  abs(rect.width()  - local_pos.x()),
            "top":    abs(local_pos.y()),
            "bottom": abs(rect.height() - local_pos.y()),
        }
        resolved = min(distances, key=lambda s: distances[s])
        if distances[resolved] <= self.GRIP_SIDE_TOLERANCE:
            return resolved
        return fallback_side or resolved

    def _resolve_target_side(self, start_point, end_point):
        if self.end_component and self.end_grip_index is not None:
            return self._resolve_grip_side(self.end_component, self.end_grip_index, self.end_side)
        if self.snap_component and self.snap_grip_index is not None:
            return self._resolve_grip_side(self.snap_component, self.snap_grip_index, self.snap_side)
        if self.end_side:
            return self.end_side
        if self.snap_side:
            return self.snap_side
        return self._guess_approach_side(start_point, end_point)

    def _guess_approach_side(self, start, end):
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        if abs(dx) > abs(dy):
            return "left" if dx > 0 else "right"
        return "top" if dy > 0 else "bottom"

    def _simplify_path(self, points):
        if len(points) < 3:
            return points

        deduped = [points[0]]
        for pt in points[1:]:
            prev = deduped[-1]
            if abs(prev.x() - pt.x()) < 0.01 and abs(prev.y() - pt.y()) < 0.01:
                continue
            deduped.append(pt)

        if len(deduped) < 3:
            return deduped

        simplified = [deduped[0]]
        for i in range(1, len(deduped) - 1):
            a = simplified[-1]
            b = deduped[i]
            c = deduped[i + 1]

            collinear_vertical = abs(a.x() - b.x()) < 0.01 and abs(b.x() - c.x()) < 0.01
            collinear_horizontal = abs(a.y() - b.y()) < 0.01 and abs(b.y() - c.y()) < 0.01
            if collinear_vertical or collinear_horizontal:
                continue

            simplified.append(b)

        simplified.append(deduped[-1])
        return simplified

    def update_path(self, components, other_connections):
        """
        High-level update:
        1. Calculate Orthogonal Path (points)
        2. Generate visual path with Jumps (QPainterPath)
        """
        self.calculate_path(components, other_connections)
        self._generate_jump_path(other_connections)

    def _generate_jump_path(self, other_connections):
        """
        Converts self.path (points) into self.painter_path (QPainterPath)
        with semi-circle jumps over intersecting connections.
        """
        self.painter_path = QPainterPath()
        if not self.path:
            return

        self.painter_path.moveTo(self.path[0])
        
        # radius of the jump
        r = 6.0 

        for i in range(len(self.path) - 1):
            p1 = self.path[i]
            p2 = self.path[i+1]
            vec = p2 - p1
            length = math.sqrt(vec.x()**2 + vec.y()**2)
            if length < 0.1: continue
            
            # Unit direction
            u = vec / length



            # Identify intersections
            # We collect (distance_from_p1, intersection_point)
            intersections = []
            
            current_seg = QLineF(p1, p2)
            
            for other in other_connections:
                if other == self: continue

                # Order-Based Jump Logic:
                # If I am older (lower index) than the other connection, I go straight (don't detect intersection).
                if self in other_connections:
                     my_index = other_connections.index(self)
                     # other is guaranteed to be in other_connections because we are iterating it
                     other_index = other_connections.index(other) # No try/except needed hopefully
                     
                     if my_index < other_index:
                         continue
                # iterate other's segments
                # We use raw points from other.path to be robust
                if not other.path: continue
                for j in range(len(other.path) - 1):
                    op1 = other.path[j]
                    op2 = other.path[j+1]
                    other_seg = QLineF(op1, op2)
                    
                    # Intersect?
                    intersection_point = QPointF()
                    type_ = current_seg.intersect(other_seg, intersection_point)
                    
                    if type_ == QLineF.BoundedIntersection:
                        # Check if it's a real crossing, not just touching endpoints
                        # and not collinear overlaps
                        dist = math.sqrt((intersection_point.x() - p1.x())**2 + (intersection_point.y() - p1.y())**2)
                        
                        # Filter out hits too close to start/end of segment (corners)
                        if r < dist < (length - r):
                            intersections.append(dist)

            intersections.sort()
            
            # Build segment with jumps
            current_dist = 0.0
            
            # De-duplicate close intersections (overlapping lines)
            clean_intersections = []
            if intersections:
                last_d = intersections[0]
                clean_intersections.append(last_d)
                for d in intersections[1:]:
                    if d - last_d > 2.2 * r: # Ensure space for jump
                        clean_intersections.append(d)
                        last_d = d

            for dist in clean_intersections:
                # Draw line to jump start
                # jump start is at dist - r
                segment_end_dist = dist - r
                
                if segment_end_dist > current_dist:
                    dest = p1 + u * segment_end_dist
                    self.painter_path.lineTo(dest)
                
                jump_center = p1 + u * dist

                
                rect_top_left = jump_center - QPointF(r, r)
                rect = QRectF(rect_top_left, QSizeF(2*r, 2*r))
                
                # Calculate angle of the line
                angle = math.degrees(math.atan2(u.y(), u.x()))
                
                self.painter_path.arcTo(rect, -angle + 180, -180) 
                # Note: Qt angles are counter-clockwise, but Y is flipped.
                # Visual Check required.
                
                current_dist = dist + r
            
            # Draw remaining line
            if current_dist < length:
                self.painter_path.lineTo(p2)


    def paint(self, painter, theme="light", zoom=1.0):
        # Determine visual width based on selection
        visual_width = 4.0 if self.is_selected else 2.5
        
        # Calculate LOGICAL width to maintain constant VISUAL width
        pen_width = visual_width / max(0.1, zoom)

        if self.is_selected:
            color = QColor("#2563eb")
            pen = QPen(color, pen_width)
            brush_color = color
        else:
            color = Qt.white if theme == "dark" else Qt.black
            pen = QPen(color, pen_width)
            brush_color = color

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        # 1. Draw The Path (with jumps)
        # Fallback to simple path if painter_path empty
        if self.painter_path.isEmpty() and self.path:
             for i in range(len(self.path)-1):
                 painter.drawLine(self.path[i], self.path[i+1])
        else:
             painter.drawPath(self.painter_path)

        # 2. Draw Arrow at End
        if len(self.path) >= 2:
            p_end = self.path[-1]
            p_prev = self.path[-2]
            
            # Vector
            vec = p_end - p_prev
            l = math.sqrt(vec.x()**2 + vec.y()**2)
            if l > 0:
                # Normalize
                u = vec / l
                
                # Arrow tip connects directly to the grip point (no retraction)
                # This ensures the connection line touches the grip exactly
                p_tip = p_end
                
                # Arrow Geometry
                # Maintain constant VISUAL size for the arrow
                visual_arrow_size = 15.0
                arrow_size = visual_arrow_size / max(0.1, zoom)
                
                # Perpendicular vector (-y, x)
                perp = QPointF(-u.y(), u.x())
                
                p_base = p_tip - u * arrow_size
                
                p1 = p_base + perp * (arrow_size / 2.5)
                p2 = p_base - perp * (arrow_size / 2.5)
                
                arrow_poly = QPolygonF([p_tip, p1, p2])
                
                # Draw Arrow with High Contrast Black Border
                # Solid Black border ensures visibility on top of EVERYTHING.
                border_width = 1.5 / max(0.1, zoom)
                painter.setPen(QPen(Qt.black, border_width))
                painter.setBrush(QBrush(brush_color))
                painter.drawPolygon(arrow_poly)
                painter.setBrush(Qt.NoBrush) # Reset
                painter.setPen(pen) # Restore pen



    def to_dict(self, component_to_id):
        """
        Serializes connection.
        component_to_id: dict mapping ComponentWidget instance -> int ID
        """
        start_id = component_to_id.get(self.start_component, -1)
        end_id = component_to_id.get(self.end_component, -1)
        
        return {
            "start_id": start_id,
            "start_grip": self.start_grip_index,
            "start_side": self.start_side,
            "end_id": end_id,
            "end_grip": self.end_grip_index,
            "end_side": self.end_side,
            "path_offset": self.path_offset,
            "start_adjust": self.start_adjust,
            "end_adjust": self.end_adjust
        }
