# Stillness Editor - Professional Requirements & Roadmap

This document serves as the high-fidelity technical blueprint for the **Stillness Editor**. It provides absolute traceability between development features, their implementation status, and verification via automated tests.

## 📊 Requirements Traceability Matrix

| ID | Feature | Level | Status | Verification / Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-CORE-01** | Isometric Grid Management & Coordinate System | 1 | **DONE** | `test_coordinate_projection` |
| **REQ-CORE-02** | Multi-Layer Rendering (Base/Objects/VFX) | 1 | **DONE** | `test_ui_distribution` |
| **REQ-CORE-03** | Map Persistence (JSON Save/Load) | 1 | **DONE** | `test_save_map_logic` |
| **REQ-CORE-04** | Version-Locked Data Integrity | 1 | **DONE** | `test_map_version_lock` |
| **REQ-CORE-05** | Robust Exception Handling (Corrupted JSON) | 1 | **DONE** | `test_map_corruption_handling` |
| **REQ-CONF-01** | Professional Dark Mode UI & Menus | 1 | **DONE** | Manual Visualization |
| **REQ-CONF-02** | Multi-Path Resource Configuration | 1 | **DONE** | `test_editor_config_loading` |
| **REQ-CONF-03** | UI Iconography (Folders, Warnings, Disk) | 1 | **DONE** | Manual Asset Check |
| **REQ-EFF-01** | Undo / Redo System (50-Step History) | 2 | PENDING | `test_undo_redo` |
| **REQ-EFF-02** | Flood Fill / Bucket Tool | 2 | PENDING | `test_bucket_fill` |
| **REQ-EFF-03** | Asset Search & Tagging System | 2 | PENDING | `test_palette_filter` |
| **REQ-ANIM-01** | Automatic Frame Sequence Detection (Batch Load) | 2 | PENDING | `test_anim_detection` |
| **REQ-EFF-04** | Region Copy / Paste Selection | 3 | PENDING | `test_copy_paste` |
| **REQ-DETAIL-01** | Prop Offsetting (Micro-nudging) | 3 | PENDING | Manual (Shift+Move) |
| **REQ-DETAIL-02** | Random Scatter Brush (Rocks/Trees) | 3 | PENDING | `test_scatter_brush` |
| **REQ-DATA-01** | Custom Entity Metadata (JSON Props) | 3 | PENDING | `test_metadata_save` |
| **REQ-ANIM-02** | In-Editor Animation Preview Panel | 4 | PENDING | Manual UI Preview |
| **REQ-ANIM-03** | Animated Character & VFX Placement | 4 | PENDING | `test_map_anim_data` |
| **REQ-SYS-01** | Dynamic Grid Expansion & Map Resizing | 4 | PENDING | `test_grid_resize` |
| **REQ-SYS-02** | 90-Degree Camera Rotation | 5 | PENDING | `test_world_rotation` |
| **REQ-SYS-03** | Depth Sorting Refinement (Z-Order Debugger) | 5 | PENDING | `test_depth_sorting` |
| **REQ-ADV-01** | Auto-Tiling Rules (Bitmasking Logic) | 5 | PENDING | `test_autotile_logic` |
| **REQ-SYS-04** | Trigger Zones & Logic Scripting Nodes | 5 | PENDING | `test_trigger_system` |
| **REQ-PIPE-01** | Git Visual Diff Visualizer | 6 | PENDING | Manual (Visual Git) |
| **REQ-PIPE-02** | Python Custom Plugin API | 6 | PENDING | `test_plugin_hooks` |
| **REQ-PIPE-03** | Real-Time Asset Hot-Reloading | 6 | PENDING | Manual File Watcher |
| **REQ-AI-01** | NavMesh Visualizer (Pathfinding) | 7 | PENDING | `test_navmesh_gen` |
| **REQ-AI-02** | Memory Budgeting & Analytics | 7 | PENDING | Manual (Stat Panel) |

---

## 🟢 Level 1: Foundations (DONE)
*Focus: Establishing the technical engine, configuration sanity, and basic rendering.*

- **REQ-CORE-01..05**: Handling of the isometric grid, coordinate projection, and robust data integrity.
- **REQ-CONF-01..03**: Professional GUI with dark themes, icons, and flexible resource paths.

---

## 🟡 Level 2: Productivity Boost (Priority: HIGH)
*Focus: Minimizing repetitive work for environmental designers.*

1. **[REQ-EFF-01] Undo / Redo Stack**: Enabling experimentation without risk of permanent errors.
2. **[REQ-EFF-02] Bucket Tool**: Smart filling of large areas (e.g., floors/water).
3. **[REQ-EFF-03] Asset Search**: Instant palette filtering by substring.
4. **[REQ-ANIM-01] Frame Batcher**: Auto-loading frame sequences from folders.

---

## 🟠 Level 3: Detail & Nuance (Priority: MEDIUM)
*Focus: Organic variety and precise placements.*

5. **[REQ-EFF-04] Selection Tools**: Copy, cut, and paste blocks of tiles and objects.
6. **[REQ-DETAIL-01] Sub-Tile Nudging**: Breaking the grid with fine-tuning offsets.
7. **[REQ-DETAIL-02] Scattering**: Painting natural environments with randomized rotation/scale.
8. **[REQ-DATA-01] Scripting Data**: Attaching properties to objects for the game engine.

---

## 🔵 Level 4: Dynamics & Flow (Priority: MEDIUM)
*Focus: Adding life and movement.*

9. **[REQ-ANIM-02] Animation Workshop**: Previsualizing playback speed (FPS) in the UI.
10. **[REQ-ANIM-03] Playback Rendering**: Integrating animated entities into the map viewport.
11. **[REQ-SYS-01] Map Flexing**: Resizing maps dynamically as levels expand.

---

## 🔴 Level 5: Spatial Logic & Systems (Priority: LOW)
*Focus: Complex spatial transformations and automated logic.*

12. **[REQ-SYS-02] Camera Spin**: Rotating the isometric view while maintaining correct Z-sorting.
13. **[REQ-SYS-03] Z-Order Debug**: Inspecting and fixing depth conflicts between overlapping assets.
14. **[REQ-ADV-01] Smart Tiling**: Implementing bitmasking for automatic terrain transitions.
15. **[REQ-SYS-04] Trigger Logic**: Defining gameplay areas and interactive scripts.

---

## 💎 Level 6: Technical Pipeline (Priority: LOW)
*Focus: Large-scale production and external tool sync.*

16. **[REQ-PIPE-01] Git Hub Sync**: Visual feedback on changes during pushes/pulls.
17. **[REQ-PIPE-03] Hot-Reload**: Instantly seeing Photoshop/Aseprite edits in the editor.
18. **[REQ-PIPE-02] Modding/Plugins API**: Extending the editor with Python hooks.

---

## 🛰️ Level 7: Intelligence & Analytics (Priority: FUTURE)
*Focus: Optimization, testing, and AI-assisted creation.*

19. **[REQ-AI-01] Pathfinding Map**: Generating NavMeshes based on map geometry.
20. **[REQ-AI-02] Stat Panel**: Analyzing VRAM, draw calls, and technical constraints.

---
*Last Updated: April 2026 - Santiago Marquez Solis*
