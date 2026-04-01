import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import pygame
from collections import deque

# Allow importing from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with patch('pygame.init'), \
     patch('pygame.display.set_mode'), \
     patch('pygame.font.SysFont'), \
     patch('pygame.Surface'):
    from src.StillnessEditor import StillnessEditor
    from src.constants import LAYER_BASE, GRID_SIZE, UNDO_LIMIT

class TestLevel2Features(unittest.TestCase):
    def setUp(self):
        with patch('pygame.display.set_mode') as mock_set_mode, \
             patch('pygame.image.load'), \
             patch('pygame.font.SysFont'), \
             patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=[]):
            
            mock_screen = MagicMock()
            mock_screen.get_size.return_value = (1920, 1080)
            mock_set_mode.return_value = mock_screen
            
            self.editor = StillnessEditor()
            self.editor.screen = mock_screen

    def test_undo_redo_logic(self):
        # 1. Initial state
        self.editor.grid[0][0]["base_id"] = None
        
        # 2. Perform action
        self.editor.save_snapshot()
        self.editor.grid[0][0]["base_id"] = "grass"
        self.assertEqual(self.editor.grid[0][0]["base_id"], "grass")
        
        # 3. Undo
        self.editor.undo()
        self.assertEqual(self.editor.grid[0][0]["base_id"], None)
        
        # 4. Redo
        self.editor.redo()
        self.assertEqual(self.editor.grid[0][0]["base_id"], "grass")

    def test_undo_limit(self):
        for i in range(UNDO_LIMIT + 10):
            self.editor.save_snapshot()
            self.editor.grid[0][0]["base_id"] = f"state_{i}"
        
        self.assertEqual(len(self.editor.undo_stack), UNDO_LIMIT)

    def test_bucket_fill(self):
        # Setup a 3x3 area of 'water'
        for x in range(3):
            for y in range(3):
                self.editor.grid[x][y]["base_id"] = "water"
        
        self.editor.selected_item = "sand"
        self.editor.current_layer = LAYER_BASE
        
        # Fill at 1,1
        self.editor.bucket_fill(1, 1)
        
        # Check all area is sand
        for x in range(3):
            for y in range(3):
                self.assertEqual(self.editor.grid[x][y]["base_id"], "sand")
        
        # Check an outside cell is still None
        self.assertEqual(self.editor.grid[4][4]["base_id"], None)

    def test_search_filter(self):
        # Mock assets
        self.editor.am.assets[LAYER_BASE] = {"main": {"grass_01": MagicMock(), "stone_01": MagicMock(), "grass_02": MagicMock()}}
        self.editor.current_layer = LAYER_BASE
        
        # No search
        self.editor.search_query = ""
        self.editor.refresh_palette()
        self.assertEqual(len(self.editor.palette_buttons), 3)
        
        # Search "grass"
        self.editor.search_query = "grass"
        self.editor.refresh_palette()
        self.assertEqual(len(self.editor.palette_buttons), 2)
        self.assertTrue(all("grass" in b["name"] for b in self.editor.palette_buttons))

    def test_animation_loading(self):
        # Manual patches to be absolutely sure they apply to src.asset_manager
        with patch('src.asset_manager.os.path.exists', return_value=True), \
             patch('src.asset_manager.os.walk') as mock_walk, \
             patch('src.asset_manager.os.listdir') as mock_listdir, \
             patch('src.asset_manager.pygame.image.load') as mock_load, \
             patch('src.asset_manager.pygame.display.get_init', return_value=False):
            
            mock_walk.return_value = [
                ('vfx', ['smoke'], []),
                ('vfx/smoke', [], ['frame_01.png', 'frame_02.png'])
            ]
            mock_listdir.return_value = ['frame_01.png', 'frame_02.png']
            
            # Use real Surfaces instead of MagicMocks to satisfy Pygame's type checks
            real_surface = pygame.Surface((100, 100))
            mock_load.return_value = real_surface
            
            config = {"asset_paths": {"vfx": "vfx"}}
            self.editor.am.load_assets(config)
            
            self.assertIn("smoke", self.editor.am.animations)
            self.assertEqual(len(self.editor.am.animations["smoke"]), 2)

if __name__ == "__main__":
    unittest.main()
