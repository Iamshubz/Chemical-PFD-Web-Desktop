import unittest
from unittest.mock import patch, Mock

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSize, QRectF, QPoint

import src.component_widget as cw


class ComponentWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls._app = QApplication([])

    def make_renderer_mock(self, w=100, h=100):
        m = Mock()
        m.defaultSize.return_value = QSize(w, h)
        m.isValid.return_value = True
        return m

    def test_calculate_logical_size_and_fixed_size(self):
        with patch("src.component_widget.QSvgRenderer") as MockRenderer:
            MockRenderer.return_value = self.make_renderer_mock(200, 100)
            widget = cw.ComponentWidget(svg_path="dummy.svg", config={})

            # logical size should be positive integers
            w, h = widget.calculate_logical_size((200, 100))
            self.assertIsInstance(w, int)
            self.assertIsInstance(h, int)
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)

    def test_get_grips_prefers_config(self):
        with patch("src.component_widget.QSvgRenderer") as MockRenderer:
            MockRenderer.return_value = self.make_renderer_mock()
            cfg = {"grips": '[{"x":0,"y":50,"side":"left"}]'}
            widget = cw.ComponentWidget(svg_path="dummy.svg", config=cfg)
            grips = widget.get_grips()
            self.assertIsInstance(grips, list)
            self.assertEqual(grips[0]["x"], 0)

    def test_get_grip_position_uses_cached_svg_rect(self):
        with patch("src.component_widget.QSvgRenderer") as MockRenderer:
            MockRenderer.return_value = self.make_renderer_mock()
            cfg = {"grips": [{"x": 0, "y": 50, "side": "left"}]}
            widget = cw.ComponentWidget(svg_path="dummy.svg", config=cfg)
            # set cached svg rect so mapping uses it
            widget._cached_svg_rect = QRectF(15, 25, 100, 100)
            p = widget.get_grip_position(0)
            self.assertIsInstance(p, QPoint)
            self.assertEqual(p.x(), 15)
            self.assertEqual(p.y(), 75)

    def test_to_dict_returns_expected(self):
        with patch("src.component_widget.QSvgRenderer") as MockRenderer:
            MockRenderer.return_value = self.make_renderer_mock()
            widget = cw.ComponentWidget(svg_path="dummy.svg", config={})
            widget.logical_rect = QRectF(10, 20, 30, 40)
            widget.rotation_angle = 45
            d = widget.to_dict()
            self.assertEqual(d["x"], 10)
            self.assertEqual(d["y"], 20)
            self.assertEqual(d["width"], 30)
            self.assertEqual(d["height"], 40)


if __name__ == "__main__":
    unittest.main()
