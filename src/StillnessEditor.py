import pygame
import sys
import os
import json
from collections import deque
import copy
from .constants import *
from .utils import world_to_screen, screen_to_world, get_file_path
from .config_manager import ConfigManager
from .asset_manager import AssetManager
from .ui_renderer import UIRenderer

class StillnessEditor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
        self.w, self.h = self.screen.get_size()
        pygame.display.set_caption(f"Stillness Point - World Editor {VERSION}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.bold_font = pygame.font.SysFont("Arial", 18, bold=True)

        # Managers
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        self.cm = ConfigManager(config_path)
        self.am = AssetManager()
        self.ui = UIRenderer(self)

        # State
        self.running = True
        self.current_layer = LAYER_BASE
        self.current_cat = None
        self.selected_item = None
        self.search_query = "" # REQ-EFF-03
        self.brush_fh = self.brush_fv = self.brush_shadow = False
        self.brush_rot = 0
        self.zoom_level = 1.0
        self.top_bar_height = 30
        self.camera_offset = pygame.Vector2(self.w // 2, self.h // 4 + self.top_bar_height)
        self.show_grid = True
        self.active_menu = None
        self.confirm_target = None
        self.modal_buttons = []
        self.ui_panel_width = 250
        self.status_message = None
        self.status_timer = 0
        
        # History (REQ-EFF-01)
        self.undo_stack = deque(maxlen=UNDO_LIMIT)
        self.redo_stack = deque(maxlen=UNDO_LIMIT)

        self.menu_items = {
            "FILE": [("New Map", "reset"), ("Open...", "load"), ("Save As...", "save"), ("Configuration", "config"), ("-", ""), ("Exit", "exit")],
            "EDIT": [("Undo [Ctrl+Z]", "undo"), ("Redo [Ctrl+Y]", "redo"), ("-", ""), ("Flip H [F]", "flip_h"), ("Flip V [V]", "flip_v"), ("Rotate [R]", "rotate"), ("Reset [X]", "clear")],
            "VIEW": [("Toggle Grid [H]", "grid"), ("Toggle Sidebar", "sidebar"), ("Fullscreen [F11]", "fs")],
            "LAYER": [("Base [1]", LAYER_BASE), ("Objects [2]", LAYER_OBJECTS), ("VFX [3]", LAYER_VFX), ("Collision [4]", LAYER_COLLISION), ("Animations [5]", LAYER_ANIM)]
        }

        self.grid = [[{
            "base_id": None, "base_fh": False, "base_fv": False, "base_rot": 0,
            "objects_id": None, "objects_fh": False, "objects_fv": False, "objects_rot": 0, "objects_shadow": False,
            "vfx_id": None, "vfx_fh": False, "vfx_fv": False, "vfx_rot": 0,
            "collision": False
        } for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        self.am.load_assets(self.cm.config)
        self.update_ui_layout()
        self.refresh_palette()

    def save_snapshot(self):
        """Saves current grid state to undo stack."""
        self.undo_stack.append(copy.deepcopy(self.grid))
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.grid))
            self.grid = self.undo_stack.pop()
            self.status_message = "UNDO"
            self.status_timer = 60

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.grid))
            self.grid = self.redo_stack.pop()
            self.status_message = "REDO"
            self.status_timer = 60

    def bucket_fill(self, start_x, start_y):
        """Fills contiguous area of same base_id with selected_item."""
        if self.current_layer != LAYER_BASE or not self.selected_item: return
        target_id = self.grid[start_x][start_y]["base_id"]
        if target_id == self.selected_item: return
        
        self.save_snapshot()
        queue = deque([(start_x, start_y)])
        visited = set([(start_x, start_y)])
        
        while queue:
            x, y = queue.popleft()
            self.grid[x][y]["base_id"] = self.selected_item
            
            for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    if (nx, ny) not in visited and self.grid[nx][ny]["base_id"] == target_id:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        self.status_message = "BUCKET FILL APPLIED"
        self.status_timer = 120

    def refresh_palette(self):
        self.palette_buttons = []
        if self.current_layer not in self.am.assets: return
        x_start, y_start = self.w - self.ui_panel_width + 10, self.top_bar_height + 360
        thumb_w, thumb_h = (self.ui_panel_width - 36) // 2, 60
        
        # Filtering logic (REQ-EFF-03)
        if self.current_layer == LAYER_ANIM:
            assets = {k: v for k, v in self.am.assets[LAYER_ANIM].items() if self.search_query.lower() in k.lower()}
            for i, (name, img) in enumerate(assets.items()):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img, "anim": True})
            return

        assets = self.am.assets[self.current_layer]
        if self.current_layer == LAYER_BASE:
            items = {k: v for k, v in assets["main"].items() if self.search_query.lower() in k.lower()}
            for i, (name, img) in enumerate(items.items()):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img})
        elif not self.current_cat:
            for i, cat in enumerate(assets):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": cat, "type": "category"})
        else:
            raw_items = assets.get(self.current_cat, {})
            items = {k: v for k, v in raw_items.items() if self.search_query.lower() in k.lower()}
            display_items = [(".. BACK", None)] + list(items.items())
            for i, (name, img) in enumerate(display_items):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                if name == ".. BACK": self.palette_buttons.append({"rect": rect, "name": name, "type": "back"})
                else: self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img})

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.VIDEORESIZE: self.w, self.h = event.w, event.h; self.update_ui_layout(); self.refresh_palette()
            if event.type == pygame.MOUSEWHEEL: self.zoom_level = max(0.2, min(4.0, self.zoom_level + event.y * 0.1))
            
            # Keyboard handling (Search & Shortcuts)
            if event.type == pygame.KEYDOWN:
                if event.mod & pygame.KMOD_CTRL:
                    if event.key == pygame.K_z: self.undo()
                    if event.key == pygame.K_y: self.redo()
                    if event.key == pygame.K_s: self.save_map()
                else:
                    if event.key == pygame.K_BACKSPACE: self.search_query = self.search_query[:-1]; self.refresh_palette()
                    elif event.key == pygame.K_ESCAPE: self.search_query = ""; self.refresh_palette()
                    elif event.unicode.isprintable(): 
                        self.search_query += event.unicode
                        self.refresh_palette()
                    
                    # Layer shortcuts
                    if event.key == pygame.K_1: self.handle_menu_action(LAYER_BASE)
                    if event.key == pygame.K_2: self.handle_menu_action(LAYER_OBJECTS)
                    if event.key == pygame.K_3: self.handle_menu_action(LAYER_VFX)
                    if event.key == pygame.K_4: self.handle_menu_action(LAYER_COLLISION)
                    if event.key == pygame.K_5: self.handle_menu_action(LAYER_ANIM)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                # Menu / Modal handling ...
                if self.active_menu:
                    m_root = next((b["rect"] for b in self.buttons if b["value"] == self.active_menu), None)
                    if m_root:
                        items = self.menu_items[self.active_menu]
                        for i, (text, val) in enumerate(items):
                            if text == "-": continue
                            if pygame.Rect(m_root.x, self.top_bar_height + i*25, 180, 25).collidepoint(mx, my):
                                self.handle_menu_action(val); self.active_menu = None; return
                    self.active_menu = None
                
                if self.confirm_target:
                    for b in self.modal_buttons:
                        if b["rect"].collidepoint(mx, my):
                            if b["value"]:
                                if self.confirm_target == "reset": self.save_snapshot(); self.grid = [[{k: (None if "id" in k else False) for k in self.grid[0][0].keys()} for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                                elif self.confirm_target == "exit": self.running = False
                            self.confirm_target = None; return

                for b in self.buttons:
                    if b["rect"].collidepoint(mx, my):
                        if b["type"] == "menu_root": self.active_menu = b["value"] if self.active_menu != b["value"] else None
                        else: self.handle_menu_action(b["value"])
                        return

                for b in self.palette_buttons:
                    if b["rect"].collidepoint(mx, my):
                        if b["type"] == "category": self.current_cat = b["name"]; self.refresh_palette()
                        elif b["type"] == "back": self.current_cat = None; self.refresh_palette()
                        else: self.selected_item = b["name"]
                        return

                gx, gy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                    if event.button == 1:
                        if event.mod & pygame.KMOD_SHIFT: # BUCKET FILL
                            self.bucket_fill(gx, gy)
                        elif self.current_layer == LAYER_COLLISION: 
                            self.save_snapshot(); self.grid[gx][gy]["collision"] = True
                        else:
                            self.save_snapshot()
                            fw, fh = self.am.get_asset_footprint(self.selected_item, self.brush_rot)
                            sx, sy = gx - fw//2, gy - fh//2
                            key = "vfx" if self.current_layer == LAYER_ANIM else self.current_layer
                            self.grid[gx][gy][f"{key}_id"] = self.selected_item
                            self.grid[gx][gy][f"{key}_rot"] = self.brush_rot
                            if self.current_layer == LAYER_OBJECTS:
                                for ix in range(fw):
                                    for iy in range(fh):
                                        if 0 <= sx+ix < GRID_SIZE and 0 <= sy+iy < GRID_SIZE: self.grid[sx+ix][sy+iy]["collision"] = True
                    elif event.button == 3:
                        self.save_snapshot()
                        if self.current_layer == LAYER_COLLISION: self.grid[gx][gy]["collision"] = False
                        else: self.grid[gx][gy][f"{self.current_layer}_id"] = None

    def run(self):
        self.ui.show_splash()
        while self.running:
            self.handle_events()
            keys = pygame.key.get_pressed()
            move_speed = 10 if keys[pygame.K_LSHIFT] else 5
            if keys[pygame.K_w]: self.camera_offset.y += move_speed
            if keys[pygame.K_s]: self.camera_offset.y -= move_speed
            if keys[pygame.K_a]: self.camera_offset.x += move_speed
            if keys[pygame.K_d]: self.camera_offset.x -= move_speed
            
            self.screen.fill(BG_COLOR)
            zw, zh = TILE_W * self.zoom_level, TILE_H * self.zoom_level
            ticks = pygame.time.get_ticks()

            for x in range(GRID_SIZE):
                for y in range(GRID_SIZE):
                    sx, sy = world_to_screen(x, y, self.zoom_level, self.camera_offset)
                    if self.show_grid: pygame.draw.polygon(self.screen, GRID_COLOR, [(sx, sy), (sx+zw//2, sy+zh//2), (sx, sy+zh), (sx-zw//2, sy+zh//2)], 1)
                    cell = self.grid[x][y]
                    for layer in [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX]:
                        item_id = cell.get(f"{layer}_id")
                        if not item_id: continue
                        
                        # Animation Logic
                        img = None
                        if item_id in self.am.animations:
                            frames = self.am.animations[item_id]
                            f_idx = (ticks // (1000 // ANIM_FPS)) % len(frames)
                            img = frames[f_idx]
                        else:
                            for cat in self.am.assets[layer].values():
                                if item_id in cat: img = cat[item_id]; break
                        
                        if img:
                            iw, ih = (int(zw), int(zh)) if layer == LAYER_BASE else (int(img.get_width()*self.zoom_level), int(img.get_height()*self.zoom_level))
                            img_s = pygame.transform.scale(img, (max(1, iw), max(1, ih)))
                            if cell.get(f"{layer}_rot", 0) != 0: img_s = pygame.transform.rotate(img_s, -cell[f"{layer}_rot"]); img_s = pygame.transform.scale(img_s, (max(1, iw), max(1, ih)))
                            if layer == LAYER_BASE: self.screen.blit(img_s, (sx - zw//2, sy))
                            else:
                                fw, fh = self.am.get_asset_footprint(item_id, cell.get(f"{layer}_rot", 0))
                                scx = (x - y) * (zw // 2) + self.camera_offset.x
                                scy = (x + y) * (zh // 2) + self.camera_offset.y
                                self.screen.blit(img_s, (scx - img_s.get_width()//2, scy + zh//2 - img_s.get_height()))

            if self.status_timer > 0: self.status_timer -= 1
            self.ui.draw_menu_bar(); self.ui.draw_dropdowns(); self.ui.draw_sidebar(); self.ui.draw_modal(); self.ui.draw_status_message(); pygame.display.flip(); self.clock.tick(60)

    def update_ui_layout(self):
        self.buttons = []
        menu_x = 10
        for menu in self.menu_items.keys():
            txt = self.font.render(menu, True, TEXT_COLOR)
            rect = pygame.Rect(menu_x, 0, txt.get_width() + 20, self.top_bar_height)
            self.buttons.append({"rect": rect, "text": menu, "type": "menu_root", "value": menu})
            menu_x += rect.width + 5
        
        tools_y = self.top_bar_height + 145
        tool_btn_w = (self.ui_panel_width - 30) // 2
        tools = [("UNDO [Z]", "undo"), ("REDO [Y]", "redo"), ("ROTATE [R]", "rotate"), ("SHADOW [G]", "shadow"), ("CLEAR [X]", "clear")]
        for i, (text, val) in enumerate(tools):
            bx = self.w - self.ui_panel_width + 10 + (i % 2) * (tool_btn_w + 10)
            by = tools_y + (i // 2) * 40
            self.buttons.append({"rect": pygame.Rect(bx, by, tool_btn_w, 30), "text": text, "type": "tool", "value": val})

        self.modal_rect = pygame.Rect(self.w//2 - 200, self.h//2 - 100, 400, 200)
        
    def handle_menu_action(self, val):
        if val in [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, LAYER_COLLISION, LAYER_ANIM]: 
            self.current_layer = val; self.current_cat = None; self.refresh_palette()
        elif val == "undo": self.undo()
        elif val == "redo": self.redo()
        elif val == "reset": self.show_confirmation("reset")
        elif val == "load": self.load_map()
        elif val == "save": self.save_map()
        elif val == "config": 
            if self.cm.change_asset_paths(): self.am.load_assets(self.cm.config); self.refresh_palette()
        elif val == "exit": self.show_confirmation("exit")
        elif val == "flip_h": self.brush_fh = not self.brush_fh
        elif val == "flip_v": self.brush_fv = not self.brush_fv
        elif val == "rotate": self.brush_rot = (self.brush_rot + 90) % 360
        elif val == "clear": self.brush_fh = self.brush_fv = self.brush_shadow = False; self.brush_rot = 0
        elif val == "grid": self.show_grid = not self.show_grid
        elif val == "sidebar": self.ui_panel_width = 250 if self.ui_panel_width == 0 else 0; self.update_ui_layout()
