import unittest

from hydrus.client.gui.canvas import ClientGUICanvasMediaLayout


class TestMediaControlsBarLayout(unittest.TestCase):
    def test_reserved_space_reduces_height(self):
        height = ClientGUICanvasMediaLayout.CalculateMediaHeightForControlsBar(
            600, 40, True, False
        )
        self.assertEqual(height, 560)

    def test_hidden_controls_bar_does_not_reserve_space(self):
        height = ClientGUICanvasMediaLayout.CalculateMediaHeightForControlsBar(
            600, 40, True, True
        )
        self.assertEqual(height, 600)

    def test_no_reserved_space_keeps_height(self):
        height = ClientGUICanvasMediaLayout.CalculateMediaHeightForControlsBar(
            600, 40, False, False
        )
        self.assertEqual(height, 600)

    def test_reserved_space_has_minimum_height(self):
        height = ClientGUICanvasMediaLayout.CalculateMediaHeightForControlsBar(
            10, 50, True, False
        )
        self.assertEqual(height, 1)
