import os

# Base Directory Resolution (Up 4 levels: src -> StillnessEditor -> tools -> StillnessPoint)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Window & Grid
WIDTH, HEIGHT = 1280, 720
TILE_W, TILE_H = 128, 64
GRID_SIZE = 15
VERSION = "v2.0 (Workbench Redesign)"

# UI Layout Dimensions
UI_TOP_BAR_H = 32
UI_LEFT_TOOLBAR_W = 52
UI_RIGHT_SIDEBAR_W = 320
UI_BOTTOM_BAR_H = 30
UI_TAB_H = 40
UI_TOOL_ICON_SIZE = 36

# Limits & Timings
UNDO_LIMIT = 50
ANIM_FPS = 12
STATUS_ERR_DURATION = 180
STATUS_OK_DURATION = 120

# Colors
BG_COLOR = (30, 30, 35)
GRID_COLOR = (60, 60, 70)
UI_COLOR = (45, 45, 50)
TEXT_COLOR = (220, 220, 220)
HIGHLIGHT_COLOR = (100, 200, 255, 100)
COLLISION_COLOR = (255, 50, 50, 150)
LABEL_COLOR = (255, 255, 100)
AXIS_COLOR_Z = (100, 100, 255)
ACCENT_COLOR = (100, 200, 255)

# Layers
LAYER_BASE = "base"
LAYER_OBJECTS = "objects"
LAYER_VFX = "vfx"
LAYER_COLLISION = "collision"
LAYER_ANIM = "animations"

# Fog Zone Constants
FOG_SHAPE_RECT = "rect"
FOG_SHAPE_ELLIPSE = "ellipse"
DEFAULT_FOG_COLOR = (220, 230, 240)
DEFAULT_FOG_DENSITY = 0.5
DEFAULT_FOG_SPEED = 0.2
DEFAULT_FOG_FEATHER = 0.25
DEFAULT_PUFF_COUNT = 40
