import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import pygame

# Allow importing from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Global Pygame Mocks
with patch('pygame.init'), \
     patch('pygame.display.set_mode'), \
     patch('pygame.font.SysFont'), \
     patch('pygame.display.set_caption'), \
     patch('pygame.mouse.set_cursor'), \
     patch('pygame.event.pump'), \
     patch('pygame.Surface'):
    from src.StillnessEditor import StillnessEditor
    from src.constants import LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, LAYER_COLLISION, GRID_SIZE, TILE_W, TILE_H, VERSION
    from src.utils import world_to_screen, screen_to_world

class TestStillnessEditorLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patchers = [
            patch('pygame.mouse.set_cursor'),
            patch('pygame.event.pump'),
            patch('pygame.display.set_mode'),
            patch('pygame.image.load'),
            patch('pygame.font.SysFont'),
            patch('pygame.draw.line'),
            patch('pygame.draw.polygon'),
            patch('pygame.draw.circle'),
            patch('pygame.draw.rect'),
            patch('os.path.exists', return_value=True),
            patch('os.listdir', return_value=[])
        ]
        for i, p in enumerate(cls.patchers):
            m = p.start()
            if i == 2: m.return_value.get_size.return_value = (1920, 1080)

    @classmethod
    def tearDownClass(cls):
        for p in cls.patchers: p.stop()

    def setUp(self):
        self.mock_screen = MagicMock()
        self.mock_screen.get_size.return_value = (1920, 1080)
        self.editor = StillnessEditor()
        self.editor.screen = self.mock_screen
        
        # Inject mock assets
        mock_img = MagicMock()
        mock_img.get_size.return_value = (100, 100)
        self.editor.am.assets[LAYER_BASE] = {"main": {"grass": mock_img}}
        # airplane_fuselage needs to exist to pass get_asset_footprint check
        self.editor.am.assets[LAYER_OBJECTS] = {"structures": {"airplane_fuselage": mock_img}}
        self.editor.selected_item = "grass"

    def test_maximized_startup(self):
        self.assertEqual(self.editor.w, 1920)

    def test_grid_initialization(self):
        self.assertEqual(len(self.editor.grid), GRID_SIZE)

    def test_coordinate_projection(self):
        gx, gy = 5, 5
        sx, sy = world_to_screen(gx, gy, self.editor.zoom_level, self.editor.camera_offset)
        rgx, rgy = screen_to_world(sx, sy, self.editor.zoom_level, self.editor.camera_offset)
        self.assertEqual(gx, rgx)
        self.assertEqual(gy, rgy)

    def test_asset_footprint_logic(self):
        # Fuselage should be 3x6
        fp = self.editor.am.get_asset_footprint("airplane_fuselage", 0)
        self.assertEqual(fp, (3, 6))
        # Rotated 90 should be 6x3
        fp_rot = self.editor.am.get_asset_footprint("airplane_fuselage", 90)
        self.assertEqual(fp_rot, (6, 3))

    def test_editor_config_loading(self):
        self.assertIn("asset_paths", self.editor.cm.config)

    def test_ui_distribution(self):
        # Verify menu roots are in buttons
        roots = [b["value"] for b in self.editor.buttons if b["type"] == "menu_root"]
        self.assertIn("FILE", roots)
        self.assertIn("EDIT", roots)

    def test_editor_config_save(self):
        # We must include the version in our assertion because the editor now always saves it
        current_version = self.editor.cm.config.get("version", VERSION)
        with patch("json.dump") as mock_dump, \
             patch("builtins.open", mock_open()):
            self.editor.cm.save_config()
            self.assertTrue(mock_dump.called)
            # The saved dict should contain the version
            saved_dict = mock_dump.call_args[0][0]
            self.assertEqual(saved_dict.get("version"), VERSION)

    def test_map_version_lock(self):
        # 1. Test loading map with CORRECT version
        correct_data = {"version": VERSION, "layers": self.editor.grid}
        with patch("json.load", return_value=correct_data), \
             patch("builtins.open", mock_open()), \
             patch("src.StillnessEditor.get_file_path", return_value="map.json"):
            self.editor.load_map()
            self.assertEqual(self.editor.grid, correct_data["layers"])

        # 2. Test loading map with WRONG version (should NOT update self.grid)
        old_grid = [[{"id": "old"}] for _ in range(GRID_SIZE)]
        self.editor.grid = old_grid
        wrong_data = {"version": "v0.0.1", "layers": [[{"id": "new"}] for _ in range(GRID_SIZE)]}
        with patch("json.load", return_value=wrong_data), \
             patch("builtins.open", mock_open()), \
             patch("src.StillnessEditor.get_file_path", return_value="map.json"):
            self.editor.load_map()
            # Grid should still be old_grid because load was blocked
            self.assertEqual(self.editor.grid, old_grid)

    def test_save_map_logic(self):
        with patch("json.dump") as mock_dump, \
             patch("builtins.open", mock_open()), \
             patch("src.StillnessEditor.get_file_path", return_value="save.json"):
            self.editor.save_map()
            self.assertTrue(mock_dump.called)
            saved_data = mock_dump.call_args[0][0]
            self.assertEqual(saved_data["version"], VERSION)
            self.assertEqual(saved_data["grid_size"], GRID_SIZE)

    def test_map_corruption_handling(self):
        # Test loading a corrupted JSON file (should not crash)
        with patch("builtins.open", mock_open(read_data="INVALID { JSON }")), \
             patch("src.StillnessEditor.get_file_path", return_value="corrupt.json"):
            # This should NOT raise JSONDecodeError but set a status_message
            try:
                self.editor.load_map()
                self.assertIn("ERROR", self.editor.status_message)
                self.assertIn("CORRUPTED", self.editor.status_message)
            except Exception as e:
                self.fail(f"load_map() raised {type(e).__name__} on corrupted file instead of handling it.")
