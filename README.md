# Stillness Point - Isometric World Editor

A professional, high-performance isometric map editor designed for the **Stillness Point** universe and future isometric projects. This tool serves as the primary engine for terrain sculpting, object placement, and visual effects orchestration.

## 🚀 Overview

The **Stillness Editor** provides a specialized 2D isometric workspace (3D-projected) with a focus on speed, precision, and atmospheric world-building. It is built using Python and Pygame, optimized for high-resolution displays and complex asset layering.

### Key Features
- **Multi-Layer Rendering**: Separate management for Base Terrain, Objects (Physical), and VFX (Additive).
- **Spatial Orientation Suite**: Real-time X/Y/Z axis markers and coordinate labels for precise alignment.
- **Dynamic UI**: Responsive top-aligned operational bar and sidebar-based asset palette.
- **Transformation Engine**: 90-degree item rotation and horizontal/vertical flipping.
- **Shadow Projection**: Integrated sprite-based shadow system for depth realism.
- **Map Persistence**: Robust JSON-based map saving and loading with file normalization.

---

## 🛠️ Installation & Execution

### Prerequisites
- Python 3.10+
- Pygame CE (Community Edition) `pip install pygame-ce`

### How to Run
From the root directory of the project:
```bash
python tools/StillnessEditor/StillnessEditor.py
```

---

## ⌨️ Controls & Shortcuts

| Key | Action |
|-----|--------|
| **W, A, S, D** | Camera Pan (Move current view) |
| **Mouse Wheel** | Zoom In / Out |
| **Mouse Left Click** | Place Item (Hold for continuous placement) |
| **Mouse Right Click** | Remove Item / Erase Collision |
| **Middle Click** | Sample Item (Pick item from grid) |
| **R** | Rotate Item (90-degree increments) |
| **F** | Flip Item Horizontally |
| **V** | Flip Item Vertically |
| **P** | Toggle Shadow (for Objects layer) |
| **H** | Toggle Grid Visibility (Preview Mode) |
| **TAB** | Cycle through Layers (Base → Objects → VFX → Collision) |
| **ESC** | Cancel Current Action or Close Modals |

---

## 📂 Asset Management

The editor automatically indexes assets from user-defined paths specified in the **Configuration**. By default:
```
/assets/
  ├── tiles/                # Base Terrain (128x64 standard)
  └── sprites/              # Objects & Props
```

### ⚙️ Configuration
The editor uses a `config.json` file to store persistent settings.
- **Custom Asset Paths**: You can redirect where the editor looks for tiles and sprites via **File -> Configuration**.
- **Persistence**: Changes are saved automatically and reloaded on startup.
- **Version Lock**: The configuration is automatically synchronized with the application version.

### 🔒 Data Integrity & Versioning
To ensure stability across updates, the Stillness Editor implements **Version-Locked File Handling**:
- **Application Version**: Every saved map includes a `"version"` field matching the current editor.
- **Strict Matching**: The editor will only load map files that exactly match the current application version. This prevents data corruption or crashes from legacy formats as the engine evolves.

### Automatic Scaling
The editor includes a built-in scaling engine to handle different asset source sizes:
- **Fuselage**: 3.0x scaling
- **Trees**: 1.8x scaling
- **VFX/God Rays**: 2.0x scaling
- **Standard Props**: 1.5x scaling

---

## 🗺️ Project Architecture

- **Engine Core**: `tools/StillnessEditor/StillnessEditor.py`
- **Unit Tests**: `tools/StillnessEditor/tests/test_editor.py`
- **Map Data**: Saved in `/map/*.json`

### The "Stillness" Standard
Maps are exported as normalized JSON files containing layer configurations, flip states, rotations, and collision flags. This format is compatible with the main game engine's tile-rendering pipeline.

---

## 📜 Future Roadmap
- [ ] **90-Degree Map Rotation**: Complete world view rotation.
- [ ] **Height-Based Sorting**: Improved Z-depth for overlapping transparent objects.
- [ ] **Animated VFX Preview**: Support for sprite-sheet animations within the editor.
- [ ] **External CLI Support**: Batch map normalization tools.

---

**Author**: Santiago Marquez Solis  
**Project**: Stillness Point (2026)  
**Website**: [www.santiagomarquezsolis.com](http://www.santiagomarquezsolis.com)

*© 2026 All rights reserved.*
