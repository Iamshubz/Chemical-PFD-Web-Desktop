import os
import sys
import importlib.util

import pytest


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


VALIDATION_MODULE_PATH = os.path.join(PROJECT_ROOT, "src", "canvas", "validation.py")
_spec = importlib.util.spec_from_file_location("desktop_validation", VALIDATION_MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
GraphValidator = _module.GraphValidator


class DummyComponent:
    def __init__(self, object_name: str):
        self.config = {"object": object_name}


class DummyConnection:
    def __init__(self, start_component, end_component):
        self.start_component = start_component
        self.end_component = end_component


@pytest.fixture
def make_component():
    def _make(object_name="pump"):
        return DummyComponent(object_name)

    return _make


def test_loop_components_are_reported(make_component):
    comp_a = make_component("pump")
    comp_b = make_component("heater")
    comp_c = make_component("cooler")

    connections = [
        DummyConnection(comp_a, comp_b),
        DummyConnection(comp_b, comp_c),
        DummyConnection(comp_c, comp_a),
    ]

    result = GraphValidator([comp_a, comp_b, comp_c], connections).validate()

    assert set(result["loops"]) == {comp_a, comp_b, comp_c}


def test_non_cyclic_graph_reports_no_loops(make_component):
    comp_a = make_component("pump")
    comp_b = make_component("heater")
    comp_c = make_component("cooler")

    connections = [
        DummyConnection(comp_a, comp_b),
        DummyConnection(comp_b, comp_c),
    ]

    result = GraphValidator([comp_a, comp_b, comp_c], connections).validate()

    assert result["loops"] == []


def test_component_with_no_in_or_out_is_flow_error(make_component):
    comp_isolated = make_component("reactor")

    result = GraphValidator([comp_isolated], []).validate()

    assert result["flow_errors"] == [comp_isolated]


def test_component_with_any_connection_is_not_flow_error(make_component):
    comp_source = make_component("inflow line")
    comp_target = make_component("pump")

    connections = [DummyConnection(comp_source, comp_target)]

    result = GraphValidator([comp_source, comp_target], connections).validate()

    assert comp_source not in result["flow_errors"]
    assert comp_target not in result["flow_errors"]


def test_dangling_connection_to_missing_component_is_ignored(make_component):
    comp_on_canvas = make_component("pump")
    comp_not_on_canvas = make_component("ghost")

    connections = [DummyConnection(comp_on_canvas, comp_not_on_canvas)]

    result = GraphValidator([comp_on_canvas], connections).validate()

    assert result["flow_errors"] == [comp_on_canvas]


def test_mixed_graph_reports_only_user_visible_failures(make_component):
    comp_a = make_component("pump")
    comp_b = make_component("valve")
    comp_c = make_component("cooler")
    comp_d = make_component("isolated vessel")

    connections = [
        DummyConnection(comp_a, comp_b),
        DummyConnection(comp_b, comp_c),
        DummyConnection(comp_c, comp_a),
    ]

    result = GraphValidator([comp_a, comp_b, comp_c, comp_d], connections).validate()

    assert set(result["loops"]) == {comp_a, comp_b, comp_c}
    assert result["flow_errors"] == [comp_d]
