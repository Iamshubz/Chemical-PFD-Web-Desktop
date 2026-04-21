import os
import sys

from PyQt5.QtCore import QPointF, QRectF


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from src.connection import Connection
import src.auto_router as auto_router


class DummyComponent:
    def __init__(self, x, y, width, height, grips):
        self.logical_rect = QRectF(x, y, width, height)
        self._grips = grips
        self._parent = None

    def parent(self):
        return self._parent

    def get_logical_grip_position(self, idx):
        grip = self._grips[idx]
        width = self.logical_rect.width()
        height = self.logical_rect.height()
        return QPointF(
            (grip["x"] / 100.0) * width,
            ((100.0 - grip["y"]) / 100.0) * height,
        )


def _segment_intersects_rect(p1, p2, rect):
    if abs(p1.y() - p2.y()) < 0.1:
        y = p1.y()
        min_x = min(p1.x(), p2.x())
        max_x = max(p1.x(), p2.x())
        return rect.top() <= y <= rect.bottom() and max_x > rect.left() and min_x < rect.right()

    if abs(p1.x() - p2.x()) < 0.1:
        x = p1.x()
        min_y = min(p1.y(), p2.y())
        max_y = max(p1.y(), p2.y())
        return rect.left() <= x <= rect.right() and max_y > rect.top() and min_y < rect.bottom()

    return False


def test_connection_path_starts_and_ends_at_grips():
    start = DummyComponent(40, 120, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    end = DummyComponent(380, 120, 100, 100, [{"x": 0, "y": 50, "side": "left"}])

    connection = Connection(start, 0, "right")
    connection.set_end_grip(end, 0, "left")

    connection.calculate_path([start, end], [])

    start_point = connection.get_start_pos()
    end_point = connection.get_end_pos()

    assert abs(connection.path[0].x() - start_point.x()) < 0.01
    assert abs(connection.path[0].y() - start_point.y()) < 0.01
    assert abs(connection.path[-1].x() - end_point.x()) < 0.01
    assert abs(connection.path[-1].y() - end_point.y()) < 0.01


def test_connection_path_is_orthogonal():
    start = DummyComponent(0, 0, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    end = DummyComponent(500, 260, 100, 100, [{"x": 0, "y": 50, "side": "left"}])

    connection = Connection(start, 0, "right")
    connection.set_end_grip(end, 0, "left")

    connection.calculate_path([start, end], [])

    assert len(connection.path) >= 2
    for i in range(len(connection.path) - 1):
        p1 = connection.path[i]
        p2 = connection.path[i + 1]
        is_horizontal = abs(p1.y() - p2.y()) < 0.01
        is_vertical = abs(p1.x() - p2.x()) < 0.01
        assert is_horizontal or is_vertical


def test_routing_avoids_blocking_component():
    start = DummyComponent(0, 100, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    end = DummyComponent(520, 100, 100, 100, [{"x": 0, "y": 50, "side": "left"}])
    obstacle = DummyComponent(240, 70, 140, 170, [{"x": 50, "y": 50, "side": "top"}])

    connection = Connection(start, 0, "right")
    connection.set_end_grip(end, 0, "left")

    connection.calculate_path([start, end, obstacle], [])

    # Use slightly inflated rect to reflect practical routing clearance behavior.
    padded_obstacle = obstacle.logical_rect.adjusted(-8, -8, 8, 8)

    for i in range(len(connection.path) - 1):
        p1 = connection.path[i]
        p2 = connection.path[i + 1]
        assert not _segment_intersects_rect(p1, p2, padded_obstacle)


def test_manual_path_mode_snaps_to_current_grips():
    start = DummyComponent(100, 100, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    end = DummyComponent(400, 260, 100, 100, [{"x": 0, "y": 50, "side": "left"}])

    connection = Connection(start, 0, "right")
    connection.set_end_grip(end, 0, "left")

    connection.is_auto_routing = False
    connection.manual_path = [
        QPointF(0, 0),
        QPointF(60, 0),
        QPointF(60, 60),
        QPointF(120, 60),
    ]

    connection.calculate_path([start, end], [])

    start_point = connection.get_start_pos()
    end_point = connection.get_end_pos()

    assert abs(connection.path[0].x() - start_point.x()) < 0.01
    assert abs(connection.path[0].y() - start_point.y()) < 0.01
    assert abs(connection.path[-1].x() - end_point.x()) < 0.01
    assert abs(connection.path[-1].y() - end_point.y()) < 0.01


def test_hit_test_detects_selected_segment():
    start = DummyComponent(0, 0, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    connection = Connection(start, 0, "right")
    connection.path = [QPointF(10, 10), QPointF(100, 10), QPointF(100, 80)]

    hit_idx = connection.hit_test(QPointF(50, 12), tolerance=5.0)

    assert hit_idx == 0


def test_auto_router_find_path_returns_orthogonal_points():
    start = QPointF(40, 40)
    end = QPointF(260, 240)
    obstacle = QRectF(120, 80, 60, 80)

    path = auto_router.find_path(
        start=start,
        end=end,
        start_side="right",
        end_side="left",
        component_rects=[obstacle],
        exclude_rects=[],
        connection_segments=[],
        canvas_bounds=QRectF(0, 0, 600, 400),
        routing_cache=None,
    )

    assert len(path) >= 2
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i + 1]
        is_horizontal = abs(p1.y() - p2.y()) < 0.01
        is_vertical = abs(p1.x() - p2.x()) < 0.01
        assert is_horizontal or is_vertical
