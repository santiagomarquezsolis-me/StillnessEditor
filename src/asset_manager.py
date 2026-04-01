import os
import pygame
from .constants import LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, TILE_W, TILE_H, BASE_DIR

class AssetManager:
    def __init__(self):
        self.assets = {LAYER_BASE: {"main": {}}, LAYER_OBJECTS: {}, LAYER_VFX: {}}
        self.asset_scales = {
            "fuselage": 3.0, "wing_left": 1.2, "wing_right": 1.2,
            "jungle_tree": 1.8, "puddle": 1.0, "god_rays": 2.0,
            "mayan_monolith_stela": 2.2, "mayan_chaac_mask_stone": 1.5,
            "mayan_broken_column": 1.4
        }

    def get_asset_footprint(self, item_id, brush_rot):
        if not item_id: return (1, 1)
        img = None
        for layer in self.assets:
            for cat in self.assets[layer].values():
                if item_id in cat: img = cat[item_id]; break
            if img: break
        if not img: return (1, 1)
        
        sw, sh = img.get_size()
        fw = max(1, round(sw / TILE_W))
        fh = fw
        
        is_structure = any(x in item_id for x in ["fuselage", "wing", "paving", "temple", "wall"])
        if is_structure:
            if "fuselage" in item_id:
                return (6, 3) if brush_rot in [90, 270] else (3, 6)
            if "wing" in item_id:
                return (1, 2) if brush_rot in [90, 270] else (2, 1)
            ratio = sh / sw
            if ratio > 1.2: fh = max(fw, round(sh / TILE_H))
            
        if brush_rot in [90, 270] and not is_structure: return (fh, fw)
        return (fw, fh)

    def load_assets(self, config):
        # Reset current assets
        self.assets = {LAYER_BASE: {"main": {}}, LAYER_OBJECTS: {}, LAYER_VFX: {}}
        paths = config.get("asset_paths", {})
        
        # 1. Load TILES
        tiles_path = paths.get("tiles")
        if tiles_path:
            full_path = tiles_path if os.path.isabs(tiles_path) else os.path.join(BASE_DIR, tiles_path)
            if os.path.exists(full_path):
                for root, _, files in os.walk(full_path):
                    for f in files:
                        if f.endswith(".png"):
                            name = f.replace(".png", "")
                            try:
                                img = pygame.image.load(os.path.join(root, f))
                                if pygame.display.get_init(): img = img.convert_alpha()
                                img = pygame.transform.smoothscale(img, (TILE_W, TILE_H))
                                self.assets[LAYER_BASE]["main"][name] = img
                            except: pass

        # 2. Load Specific Categories (Rocks, Structures, VFX)
        categories = {
            "rocks": LAYER_OBJECTS,
            "structures": LAYER_OBJECTS,
            "vfx": LAYER_VFX
        }
        
        for key, layer in categories.items():
            path = paths.get(key)
            if not path: continue
            
            full_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
            if os.path.exists(full_path):
                cat_name = key
                if cat_name not in self.assets[layer]: self.assets[layer][cat_name] = {}
                
                for root, _, files in os.walk(full_path):
                    for f in files:
                        if f.endswith(".png"):
                            pygame.event.pump()
                            name = f.replace(".png", "")
                            try:
                                img = pygame.image.load(os.path.join(root, f))
                                if pygame.display.get_init(): img = img.convert_alpha()
                                
                                # Apply scaling factors
                                scale_factor = 1.5
                                for s_key, val in self.asset_scales.items():
                                    if s_key in name: scale_factor = val; break
                                
                                target_w = TILE_W * scale_factor
                                aspect = img.get_width() / img.get_height()
                                new_w, new_h = int(target_w), int(target_w / aspect)
                                img = pygame.transform.smoothscale(img, (max(1, new_w), max(1, new_h)))
                                self.assets[layer][cat_name][name] = img
                            except: pass

        # 3. Legacy sprites path support (optional, can be empty)
        sprites_path = paths.get("sprites")
        if sprites_path:
            full_path = sprites_path if os.path.isabs(sprites_path) else os.path.join(BASE_DIR, sprites_path)
            if os.path.exists(full_path):
                for root, _, files in os.walk(full_path):
                    cat_name = os.path.basename(root)
                    if cat_name == "sprites": continue
                    for f in files:
                        if f.endswith(".png"):
                            name = f.replace(".png", "")
                            try:
                                # ... existing logic for general sprites ...
                                pass
                            except: pass
