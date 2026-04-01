import os
import pygame
from .constants import LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, LAYER_ANIM, TILE_W, TILE_H, BASE_DIR

class AssetManager:
    def __init__(self):
        self.assets = {LAYER_BASE: {"main": {}}, LAYER_OBJECTS: {}, LAYER_VFX: {}, LAYER_ANIM: {}}
        self.animations = {} # { "anim_name": [pygame.Surface, ...] }
        self.asset_scales = {
            "fuselage": 3.0, "wing": 1.2, "jungle_tree": 1.8, 
            "monolith": 2.2, "chaac": 1.5, "column": 1.4,
            "smoke": 1.5, "fire": 1.2
        }

    def load_assets(self, config):
        # Reset current assets & animations
        self.assets = {LAYER_BASE: {"main": {}}, LAYER_OBJECTS: {}, LAYER_VFX: {}, LAYER_ANIM: {}}
        self.animations = {}
        paths = config.get("asset_paths", {})
        
        # 1. Load Static Assets (Tiles, Rocks, Structures, VFX)
        categories = {
            "tiles": LAYER_BASE,
            "rocks": LAYER_OBJECTS,
            "structures": LAYER_OBJECTS,
            "vfx": LAYER_VFX
        }
        
        for key, layer in categories.items():
            path = paths.get(key)
            if not path: continue
            
            full_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
            if os.path.exists(full_path):
                # Use 'main' for LAYER_BASE to match UI expectations
                cat_name = "main" if layer == LAYER_BASE else key
                if cat_name not in self.assets[layer]: self.assets[layer][cat_name] = {}
                
                for root, dirs, files in os.walk(full_path):
                    # Check for Animation Subdirectories
                    for d in dirs:
                        anim_path = os.path.join(root, d)
                        frames = self._load_animation_frames(anim_path)
                        if frames:
                            self.animations[d] = frames
                            # Add representative thumb to LAYER_ANIM
                            self.assets[LAYER_ANIM][d] = frames[0]
                    
                    # Load individual files (if not part of an animation folder)
                    for f in files:
                        if f.endswith(".png"):
                            name = f.replace(".png", "")
                            # Avoid loading individual frames as static assets if they are in an anim folder
                            if any(name.startswith(a) for a in self.animations): continue
                            
                            try:
                                img = self._prepare_img(os.path.join(root, f), name, layer)
                                if img: self.assets[layer][cat_name][name] = img
                            except: pass

    def _load_animation_frames(self, path):
        """Loads a sequence of frames from a directory."""
        files = sorted([f for f in os.listdir(path) if f.endswith(".png")])
        if not files: return None
        
        frames = []
        name = os.path.basename(path)
        for f in files:
            img = self._prepare_img(os.path.join(path, f), name, LAYER_VFX) # Scale like VFX
            if img: frames.append(img)
        return frames if len(frames) > 1 else None

    def _prepare_img(self, path, name, layer):
        img = pygame.image.load(path)
        if pygame.display.get_init(): img = img.convert_alpha()
        
        # Base layer is always TILE_W x TILE_H
        if layer == LAYER_BASE:
            return pygame.transform.smoothscale(img, (TILE_W, TILE_H))
            
        # Others use scaling factors
        scale_factor = 1.5
        for s_key, val in self.asset_scales.items():
            if s_key.lower() in name.lower(): scale_factor = val; break
        
        target_w = TILE_W * scale_factor
        aspect = img.get_width() / img.get_height()
        new_w, new_h = int(target_w), int(target_w / aspect)
        return pygame.transform.smoothscale(img, (max(1, new_w), max(1, new_h)))

    def get_asset_footprint(self, item_id, brush_rot):
        if not item_id: return (1, 1)
        
        # Check animations first
        if item_id in self.animations:
            img = self.animations[item_id][0]
        else:
            img = None
            for layer in self.assets:
                for cat in self.assets[layer].values():
                    if item_id in cat: img = cat[item_id]; break
                if img: break
                
        if not img: return (1, 1)
        
        sw, sh = img.get_size()
        fw = max(1, round(sw / TILE_W))
        fh = fw
        
        is_struct = any(x in item_id.lower() for x in ["fuselage", "wing", "paving", "temple", "wall", "monolith"])
        if is_struct:
            if "fuselage" in item_id.lower(): return (6, 3) if brush_rot in [90, 270] else (3, 6)
            if "wing" in item_id.lower(): return (1, 2) if brush_rot in [90, 270] else (2, 1)
            ratio = sh / sw
            if ratio > 1.2: fh = max(fw, round(sh / TILE_H))
            
        if brush_rot in [90, 270] and not is_struct: return (fh, fw)
        return (fw, fh)
