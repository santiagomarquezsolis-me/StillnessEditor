import pygame
import sys
import os
import json

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
        self.current_cat = None # FIXED: Added missing initialization
        self.selected_item = None
        self.brush_fh = self.brush_fv = self.brush_shadow = False
        self.brush_rot = 0
        self.zoom_level = 1.0
        self.MIN_ZOOM, self.MAX_ZOOM, self.ZOOM_STEP = 0.2, 4.0, 0.1
        self.top_bar_height = 30
        self.camera_offset = pygame.Vector2(self.w // 2, self.h // 4 + self.top_bar_height)
        self.show_grid = True
        self.active_menu = None
        self.confirm_target = None
        self.ui_panel_width = 250
        self.layer_visibility = {LAYER_BASE: True, LAYER_OBJECTS: True, LAYER_VFX: True, LAYER_COLLISION: True}
        self.status_message = None
        self.status_timer = 0
        
        self.menu_items = {
            "FILE": [("New Map", "reset"), ("Open...", "load"), ("Save As...", "save"), ("Configuration", "config"), ("-", ""), ("Exit", "exit")],
            "EDIT": [("Flip Horizontal [F]", "flip_h"), ("Flip Vertical [V]", "flip_v"), ("Rotate 90 [R]", "rotate"), ("Reset Transforms [X]", "clear")],
            "VIEW": [("Toggle Grid [H]", "grid"), ("Toggle Sidebar", "sidebar"), ("Fullscreen [F11]", "fs")],
            "LAYER": [("Base [Tab]", LAYER_BASE), ("Objects", LAYER_OBJECTS), ("VFX", LAYER_VFX), ("Collision", LAYER_COLLISION)]
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
        tools = [("FLIP H [F]", "flip_h"), ("FLIP V [V]", "flip_v"), ("ROTATE [R]", "rotate"), ("SHADOW [G]", "shadow"), ("CLEAR [X]", "clear")]
        for i, (text, val) in enumerate(tools):
            bx = self.w - self.ui_panel_width + 10 + (i % 2) * (tool_btn_w + 10)
            by = tools_y + (i // 2) * 40
            self.buttons.append({"rect": pygame.Rect(bx, by, tool_btn_w, 30), "text": text, "type": "tool", "value": val})

        self.modal_rect = pygame.Rect(self.w//2 - 200, self.h//2 - 100, 400, 200)
        if self.confirm_target: self.show_confirmation(self.confirm_target)

    def refresh_palette(self):
        self.palette_buttons = []
        if self.current_layer not in self.am.assets: return
        x_start, y_start = self.w - self.ui_panel_width + 10, self.top_bar_height + 360
        thumb_w, thumb_h = (self.ui_panel_width - 36) // 2, 60
        assets = self.am.assets[self.current_layer]
        
        if self.current_layer == LAYER_BASE:
            for i, name in enumerate(assets["main"]):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": assets["main"][name]})
        elif not self.current_cat:
            for i, cat in enumerate(assets):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": cat, "type": "category"})
        else:
            items = [".. BACK"] + list(assets.get(self.current_cat, {}).keys())
            for i, name in enumerate(items):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                if name == ".. BACK": self.palette_buttons.append({"rect": rect, "name": name, "type": "back"})
                else: self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": assets[self.current_cat][name]})

    def handle_menu_action(self, val):
        if val in [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, LAYER_COLLISION]: 
            self.current_layer = val; self.current_cat = None; self.refresh_palette()
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

    def show_confirmation(self, target):
        self.confirm_target = target
        self.modal_buttons = []
        y_pos = self.modal_rect.bottom - 60
        self.modal_buttons.append({"rect": pygame.Rect(self.modal_rect.centerx - 120, y_pos, 100, 40), "text": "YES", "value": True})
        self.modal_buttons.append({"rect": pygame.Rect(self.modal_rect.centerx + 20, y_pos, 100, 40), "text": "NO", "value": False})

    def save_map(self):
        path = get_file_path("save")
        if path:
            data = {
                "version": VERSION,
                "grid_size": GRID_SIZE,
                "layers": self.grid
            }
            with open(path, "w") as f: json.dump(data, f, indent=4)

    def load_map(self):
        path = get_file_path("load")
        if not path: return
        
        try:
            with open(path, "r") as f:
                # El blindaje comienza aquí: verificamos que el archivo no esté vacío
                content = f.read().strip()
                if not content:
                    raise json.JSONDecodeError("File is empty", "", 0)
                
                data = json.loads(content)
                
                # Verificación de integridad básica
                if "layers" not in data:
                    self.status_message = "ERROR: INVALID MAP FORMAT"
                    self.status_timer = 180
                    return
                
                # Verificación de versión (aviso pero permite cargar si es posible)
                if data.get("version") != VERSION:
                    self.status_message = f"VERSION ERROR: {data.get('version')}"
                    self.status_timer = 180
                    return
                
                self.grid = data["layers"]
                self.status_message = "MAP LOADED"
                self.status_timer = 120
                self.refresh_palette()
                
        except json.JSONDecodeError:
            self.status_message = "ERROR: CORRUPTED FILE (JSON)"
            self.status_timer = 240 # Más tiempo para leer el error crítico
        except FileNotFoundError:
            self.status_message = "ERROR: FILE NOT FOUND"
            self.status_timer = 180
        except Exception as e:
            # Captura cualquier otro error inesperado sin cerrar el editor
            self.status_message = f"ERROR: LOAD FAILED"
            self.status_timer = 180

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.VIDEORESIZE: self.w, self.h = event.w, event.h; self.update_ui_layout(); self.refresh_palette()
            if event.type == pygame.MOUSEWHEEL: self.zoom_level = max(0.2, min(4.0, self.zoom_level + event.y * 0.1))
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
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
                                if self.confirm_target == "reset": self.grid = [[{k: (None if "id" in k else False) for k in self.grid[0][0].keys()} for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
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
                        if self.current_layer == LAYER_COLLISION: self.grid[gx][gy]["collision"] = True
                        else:
                            fw, fh = self.am.get_asset_footprint(self.selected_item, self.brush_rot)
                            sx, sy = gx - fw//2, gy - fh//2
                            self.grid[gx][gy][f"{self.current_layer}_id"] = self.selected_item
                            self.grid[gx][gy][f"{self.current_layer}_rot"] = self.brush_rot
                            if self.current_layer == LAYER_OBJECTS:
                                for ix in range(fw):
                                    for iy in range(fh):
                                        if 0 <= sx+ix < GRID_SIZE and 0 <= sy+iy < GRID_SIZE: self.grid[sx+ix][sy+iy]["collision"] = True
                    elif event.button == 3:
                        if self.current_layer == LAYER_COLLISION: self.grid[gx][gy]["collision"] = False
                        else: self.grid[gx][gy][f"{self.current_layer}_id"] = None

    def run(self):
        self.ui.show_splash()
        while self.running:
            self.handle_events()
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]: self.camera_offset.y += 5
            if keys[pygame.K_s]: self.camera_offset.y -= 5
            if keys[pygame.K_a]: self.camera_offset.x += 5
            if keys[pygame.K_d]: self.camera_offset.x -= 5
            
            self.screen.fill(BG_COLOR)
            zw, zh = TILE_W * self.zoom_level, TILE_H * self.zoom_level
            for x in range(GRID_SIZE):
                for y in range(GRID_SIZE):
                    sx, sy = world_to_screen(x, y, self.zoom_level, self.camera_offset)
                    if self.show_grid: pygame.draw.polygon(self.screen, GRID_COLOR, [(sx, sy), (sx+zw//2, sy+zh//2), (sx, sy+zh), (sx-zw//2, sy+zh//2)], 1)
                    cell = self.grid[x][y]
                    for layer in [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX]:
                        item_id = cell.get(f"{layer}_id")
                        if not item_id: continue
                        img = None
                        for cat in self.am.assets[layer].values():
                            if item_id in cat: img = cat[item_id]; break
                        if img:
                            iw, ih = (int(zw), int(zh)) if layer == LAYER_BASE else (int(img.get_width()*self.zoom_level), int(img.get_height()*self.zoom_level))
                            img_s = pygame.transform.scale(img, (max(1, iw), max(1, ih)))
                            if cell.get(f"{layer}_rot", 0) != 0: img_s = pygame.transform.rotate(img_s, -cell[f"{layer}_rot"]); img_s = pygame.transform.scale(img_s, (max(1, iw), max(1, ih)))
                            if layer == LAYER_BASE: self.screen.blit(img_s, (sx - zw//2, sy))
                            else:
                                fw, fh = self.am.get_asset_footprint(item_id, cell.get(f"{layer}_rot", 0))
                                st_x, st_y = x - fw//2, y - fh//2
                                cx, cy = st_x + (fw-1)/2.0, st_y + (fh-1)/2.0
                                scx = (cx-cy)*(zw//2) + self.camera_offset.x
                                scy = (cx+cy)*(zh//2) + self.camera_offset.y
                                self.screen.blit(img_s, (scx - img_s.get_width()//2, scy + zh//2 - img_s.get_height()))
                    if cell["collision"] and self.current_layer == LAYER_COLLISION:
                        s = pygame.Surface((zw, zh), pygame.SRCALPHA); pygame.draw.polygon(s, COLLISION_COLOR, [(zw//2, 0), (zw, zh//2), (zw//2, zh), (0, zh//2)]); self.screen.blit(s, (sx - zw//2, sy))
            if self.status_timer > 0: self.status_timer -= 1
            self.ui.draw_menu_bar(); self.ui.draw_dropdowns(); self.ui.draw_sidebar(); self.ui.draw_modal(); self.ui.draw_status_message(); pygame.display.flip(); self.clock.tick(60)
