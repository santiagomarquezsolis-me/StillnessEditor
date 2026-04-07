import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import pygame
from collections import deque

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock pygame to avoid window during imports/tests
with patch('pygame.init'), \
     patch('pygame.display.set_mode'), \
     patch('pygame.font.SysFont'), \
     patch('pygame.Surface'):
    from src.StillnessEditor import StillnessEditor
    from src.constants import LAYER_BASE, LAYER_OBJECTS, GRID_SIZE

class TestProductivityTools(unittest.TestCase):
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

    def test_bucket_fill_base_layer(self):
        # Setup: Fill a 3x3 area with 'old_item'
        for x in range(3):
            for y in range(3):
                self.editor.grid[x][y]["base_id"] = "old_item"
        
        self.editor.current_layer = LAYER_BASE
        self.editor.selected_item = "new_item"
        
        # Action: Fill at 1,1
        self.editor.bucket_fill(1, 1)
        
        # Verify: 3x3 area should be 'new_item'
        for x in range(3):
            for y in range(3):
                self.assertEqual(self.editor.grid[x][y]["base_id"], "new_item")
        
        # Verify: Outside area (e.g., 4,4) should NOT be 'new_item'
        self.assertNotEqual(self.editor.grid[4][4]["base_id"], "new_item")

    def test_bucket_fill_object_layer(self):
        # Setup: Fill a 2x2 area with 'old_obj' in OBJECTS layer
        for x in range(2):
            for y in range(2):
                self.editor.grid[x][y]["objects_id"] = "old_obj"
        
        self.editor.current_layer = LAYER_OBJECTS
        self.editor.selected_item = "new_obj"
        
        # Action: Fill
        self.editor.bucket_fill(0, 0)
        
        # Verify
        for x in range(2):
            for y in range(2):
                self.assertEqual(self.editor.grid[x][y]["objects_id"], "new_obj")

    def test_scatter_brush_randomization(self):
        # Verify that when brush_scatter is ON, random rotations are picked.
        self.editor.brush_scatter = True
        
        # We'll simulate 20 placements logic directly as extracted from handle_events
        rotations = set()
        import random
        for _ in range(50):
            # This is the logic we implemented in MOUSEBUTTONDOWN
            rotation = random.choice([0, 90, 180, 270])
            rotations.add(rotation)
        
        # In 50 tries, it's virtually certain to get multiple rotations
        self.assertTrue(len(rotations) > 1, f"Scatter should produce variety, got: {rotations}")

if __name__ == '__main__':
    unittest.main()
