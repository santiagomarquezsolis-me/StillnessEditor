# Stillness Editor - Technical Requirements Roadmap

This document outlines the evolutionary path of the **Stillness Editor** from a functional tool to a professional-grade isometric production suite. Requirements are ordered by **Increasing Implementation Complexity**.

---

## 🟢 Level 1: Workflow Efficiency (Low Complexity)
*Focus: Improving the daily speed of the map designer.*

1.  **Undo / Redo System**: Implementation of a command history stack (Standard 50-step limit).
2.  **Fill / Bucket Tool**: Flooding an area with a selected base tile (4-way adjacency check).
3.  **Asset Search & Tagging**: Search bar in the palette to filter assets by name (e.g., "stone", "tree").
4.  **Layer Visibility Modes**: Individual toggles to hide/show specific layers (Base, Objects, VFX, Collision).
5.  **Multi-Brush Sizes**: Support for 3x3 and 5x5 square brushes for faster terrain painting.

---

## 🟡 Level 2: Organic Detailing (Medium Complexity)
*Focus: Breaking the "grid" feel and adding life to the world.*

6.  **Prop Offsetting**: Fine-tuning the (x, y) coordinates of an object within its tile (Shift-click to nudge).
7.  **Random Scatter Brush**: Placing items from a set (e.g., "Rocks") with randomized rotation and minor offsets to create natural looks.
8.  **Internal File Explorer**: A dedicated UI panel to switch between map files without OS dialogs.
9.  **Entity Metadata**: A UI form to attach custom JSON properties to placed objects (e.g., `locked: true`, `trigger_id: 101`).

---

## 🟠 Level 3: Spatial Logic & Systems (High Complexity)
*Focus: Deep architectural changes and game logic integration.*

10. **90-Degree Camera Rotation**: Rotating the entire world view while maintaining consistent depth sorting (Z-order recalculation).
11. **Dynamic Map Resizing**: Expanding or cropping the map grid in any direction without losing existing data.
12. **Trigger Zones & Nodes**: Vector-based or grid-based "Logic Areas" for scripts (Combat zones, cinematic triggers).
13. **Prefab System**: Selecting a cluster of tiles/objects and saving them as a single "stamp" for reuse.

---

## 🔴 Level 4: Engine Integration (Advanced Complexity)
*Focus: Real-time visual parity with the game engine.*

14. **Auto-Tiling Logic**: Intelligent terrain placement based on neighbor rules (Corner/Edge detection).
15. **Lighting Strategy Preview**: Placing light sources and visualizing shadow/light falloff using additive masks.
16. **Animated Tile Support**: Real-time preview of multi-frame animations (Water, flickering neon, smoke).
17. **Particle Emitters**: Visualizing particle flow (Dust, fire) directly in the editor using the game's actual particle logic.

---

## 💎 Level 5: Professional Pipeline (Elite Complexity)
*Focus: Large-scale production and external tool parity.*

18. **Version Control Integration**: Visual "Diff" showing changes between the current map and the last Git commit.
19. **Collaborative Editing Mode**: (Future) Multiple designers working on the same large map (Shared memory/Network).
20. **Custom Plugin API**: Python-based hooks to allow external scripts to generate procedural terrain or cleanup maps.
21. **Asset Variation (Alt-Tiles)**: Automatically cycle through variations of a single asset (e.g., "Grass_01...04") during painting to avoid repetition.
22. **Live Asset Hot-Reloading**: Real-time update of textures/sprites in the editor when the source files are edited in external software (Photoshop/Aseprite).

---

## 🛰️ Level 6: Analytics & AI (Future-Proofing)
*Focus: Optimization, testing, and AI-assisted design.*

23. **Project Statistics & Memory Budget**: Counting unique textures and predicting VRAM usage for the target platform (Console/Mobile).
24. **Navigation Mesh (Path-finding) Visualizer**: Real-time heat-map showing where entities can walk based on collision and height.
25. **Layer Groups / Folders**: Organizing complex maps with 10+ layers (e.g., "Forest_L01", "Interior_Ground").
26. **Batch Processing Tools**: Global operations like "Replace all Stone_01 with Mossy_Stone_01" or "Translate all objects by 2 units".
27. **Tile Animation Curves**: Fine-tuning the speed and ease of animated tiles (Water waves, flickering embers).
28. **Z-Order Debugger**: A specialized tool to inspect the exact sorting order of overlapping high-res sprites.
29. **Heightmap & Multi-Floor logic**: Defining absolute Z-heights (Floor 1, Floor 2) for complex vertical architecture.
30. **External Scripting Console**: A built-in terminal to run Python commands directly against the current grid state.

---
*Last Updated: April 2026*
