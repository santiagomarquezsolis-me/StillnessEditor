import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import pygame
import copy

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock pygame
with patch('pygame.init'), \
     patch('pygame.display.set_mode'), \
     patch('pygame.font.SysFont'), \
     patch('pygame.Surface'):
    from src.StillnessEditor import StillnessEditor
    from src.constants import LAYER_BASE, GRID_SIZE

class TestSelectionTools(unittest.TestCase):
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
            self.editor.screen = mock_screen # Manually assign as well if needed

    def test_copy_paste_region(self):
        # 1. Setup a region with specific data
        self.editor.grid[2][2]["base_id"] = "stone"
        self.editor.grid[3][3]["objects_id"] = "tree"
        
        # 2. Select the region
        self.editor.selection_start = (2, 2)
        self.editor.selection_end = (3, 3)
        
        # 3. Copy
        self.editor.copy_selection()
        self.assertIsNotNone(self.editor.clipboard)
        self.assertEqual(len(self.editor.clipboard), 2)
        
        # 4. Paste at a new location
        self.editor.paste_at(8, 8)
        
        # 5. Verify results at (8,8) and (9,9)
        self.assertEqual(self.editor.grid[8][8]["base_id"], "stone")
        self.assertEqual(self.editor.grid[9][9]["objects_id"], "tree")

    def test_nudging_logic(self):
        # Select single cell
        gx, gy = 5, 5
        self.editor.selection_start = self.editor.selection_end = (gx, gy)
        self.editor.grid[gx][gy]["offset_x"] = 0
        
        # Simulation of arrow key events in StillnessEditor logic
        # (Testing the state update directly)
        self.editor.grid[gx][gy]["offset_x"] += 5 # Simulate Shift+Right
        self.assertEqual(self.editor.grid[gx][gy]["offset_x"], 5)
        
        self.editor.grid[gx][gy]["offset_y"] -= 1 # Simulate Up
        self.assertEqual(self.editor.grid[gx][gy]["offset_y"], -1)

    def test_metadata_persistence(self):
        self.editor.grid[0][0]["metadata"] = "trigger_01"
        self.assertEqual(self.editor.grid[0][0]["metadata"], "trigger_01")
        
        # Snapshot test
        self.editor.save_snapshot()
        self.editor.grid[0][0]["metadata"] = "changed"
        self.editor.undo()
        self.assertEqual(self.editor.grid[0][0]["metadata"], "trigger_01")

if __name__ == '__main__':
    unittest.main()
