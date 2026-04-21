import os
import sys

from PyQt5.QtCore import QPointF, QRectF

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.connection import Connection
from src.canvas.validation import GraphValidator


class DummyComponent:
    def __init__(self, x, y, width, height, grips):
        self.logical_rect = QRectF(x, y, width, height)
        self._grips = grips
        self.config = {"object": "generic"}

    def get_logical_grip_position(self, idx):
        grip = self._grips[idx]
        width = self.logical_rect.width()
        height = self.logical_rect.height()
        return QPointF(
            (grip["x"] / 100.0) * width,
            ((100.0 - grip["y"]) / 100.0) * height,
        )


class DummyConnection:
    def __init__(self, start_component, end_component, start_grip, end_grip, path):
        self.start_component = start_component
        self.end_component = end_component
        self.start_grip_index = start_grip
        self.end_grip_index = end_grip
        self.path = path


def _segment_intersects_rect(p1, p2, rect):
    if abs(p1.y() - p2.y()) < 0.1:
        y = p1.y()
        min_x = min(p1.x(), p2.x())
        max_x = max(p1.x(), p2.x())
        return (
            rect.top() <= y <= rect.bottom()
            and max_x > rect.left()
            and min_x < rect.right()
        )

    if abs(p1.x() - p2.x()) < 0.1:
        x = p1.x()
        min_y = min(p1.y(), p2.y())
        max_y = max(p1.y(), p2.y())
        return (
            rect.left() <= x <= rect.right()
            and max_y > rect.top()
            and min_y < rect.bottom()
        )

    return False


def test_routing_resolves_start_side_from_grip_geometry():
    start = DummyComponent(0, 0, 100, 100, [{"x": 50, "y": 100, "side": "right"}])
    end = DummyComponent(0, -220, 100, 100, [{"x": 50, "y": 0, "side": "left"}])

    connection = Connection(start, 0, "right")
    connection.set_end_grip(end, 0, "left")

    connection.calculate_path([start, end], [])

    start_point = connection.get_start_pos()
    assert abs(connection.path[0].x() - start_point.x()) < 0.01
    assert abs(connection.path[0].y() - start_point.y()) < 0.01

    first_stub_point = connection.path[1]
    assert abs(first_stub_point.x() - start_point.x()) < 0.01
    assert first_stub_point.y() < start_point.y()


def test_connection_endpoints_snap_exactly_to_grips():
    start = DummyComponent(40, 120, 100, 100, [{"x": 100, "y": 50, "side": "left"}])
    end = DummyComponent(380, 120, 100, 100, [{"x": 0, "y": 50, "side": "right"}])

    connection = Connection(start, 0, "left")
    connection.set_end_grip(end, 0, "right")

    connection.calculate_path([start, end], [])

    start_point = connection.get_start_pos()
    end_point = connection.get_end_pos()

    assert abs(connection.path[0].x() - start_point.x()) < 0.01
    assert abs(connection.path[0].y() - start_point.y()) < 0.01
    assert abs(connection.path[-1].x() - end_point.x()) < 0.01
    assert abs(connection.path[-1].y() - end_point.y()) < 0.01


def test_routing_avoids_crossing_middle_component():
    start = DummyComponent(0, 100, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    end = DummyComponent(420, 100, 100, 100, [{"x": 0, "y": 50, "side": "left"}])
    obstacle = DummyComponent(200, 80, 120, 140, [{"x": 50, "y": 50, "side": "top"}])

    connection = Connection(start, 0, "right")
    connection.set_end_grip(end, 0, "left")

    connection.calculate_path([start, end, obstacle], [])

    padded_obstacle = obstacle.logical_rect.adjusted(-10, -10, 10, 10)
    for idx in range(len(connection.path) - 1):
        p1 = connection.path[idx]
        p2 = connection.path[idx + 1]
        assert not _segment_intersects_rect(p1, p2, padded_obstacle)


def test_final_path_never_reenters_component_after_simplify():
    start = DummyComponent(0, 200, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    end = DummyComponent(600, 200, 100, 100, [{"x": 0, "y": 50, "side": "left"}])
    obstacle_a = DummyComponent(220, 120, 120, 140, [{"x": 50, "y": 50, "side": "top"}])
    obstacle_b = DummyComponent(360, 220, 120, 140, [{"x": 50, "y": 50, "side": "top"}])

    connection = Connection(start, 0, "right")
    connection.set_end_grip(end, 0, "left")

    connection.calculate_path([start, end, obstacle_a, obstacle_b], [])

    padded_rects = [
        obstacle_a.logical_rect.adjusted(-10, -10, 10, 10),
        obstacle_b.logical_rect.adjusted(-10, -10, 10, 10),
    ]

    for idx in range(len(connection.path) - 1):
        p1 = connection.path[idx]
        p2 = connection.path[idx + 1]
        assert not any(_segment_intersects_rect(p1, p2, rect) for rect in padded_rects)


def test_validation_accepts_small_endpoint_offset_at_ports():
    inlet = DummyComponent(0, 0, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    outlet = DummyComponent(250, 0, 100, 100, [{"x": 0, "y": 50, "side": "left"}])
    inlet.config = {"object": "inflow line"}
    outlet.config = {"object": "outflow line"}

    start_anchor = inlet.logical_rect.topLeft() + inlet.get_logical_grip_position(0)
    end_anchor = outlet.logical_rect.topLeft() + outlet.get_logical_grip_position(0)

    conn = DummyConnection(
        inlet,
        outlet,
        0,
        0,
        [
            QPointF(start_anchor.x() + 1.0, start_anchor.y() + 0.5),
            QPointF(end_anchor.x() - 0.5, end_anchor.y() - 1.0),
        ],
    )

    result = GraphValidator([inlet, outlet], [conn]).validate()
    assert inlet not in result["isolated"]
    assert outlet not in result["isolated"]


def test_validation_rejects_large_endpoint_offset_from_ports():
    inlet = DummyComponent(0, 0, 100, 100, [{"x": 100, "y": 50, "side": "right"}])
    outlet = DummyComponent(250, 0, 100, 100, [{"x": 0, "y": 50, "side": "left"}])
    inlet.config = {"object": "inflow line"}
    outlet.config = {"object": "outflow line"}

    start_anchor = inlet.logical_rect.topLeft() + inlet.get_logical_grip_position(0)
    end_anchor = outlet.logical_rect.topLeft() + outlet.get_logical_grip_position(0)

    conn = DummyConnection(
        inlet,
        outlet,
        0,
        0,
        [
            QPointF(start_anchor.x() + 7.0, start_anchor.y()),
            QPointF(end_anchor.x(), end_anchor.y() + 7.0),
        ],
    )

    result = GraphValidator([inlet, outlet], [conn]).validate()
    assert inlet in result["isolated"]
    assert outlet in result["isolated"]
