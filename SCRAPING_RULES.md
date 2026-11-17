# Automated Feature Exploration & Screen Recording Specification

This specification defines the universal protocol and rules governing automated UI exploration, dynamic interaction, and screen recording across all Data Science, AI, and Machine Learning project showcases (both Localhost servers and live Vercel/Cloud deployments).

---

## 1. Core Mission: Zero Time Limits & Complete Exhaustive Exploration
Every recording must serve as a **comprehensive, unhurried, production-grade video demonstration**. 
- **No Artificial Time Limits**: There is no rigid 15s or 30s cap. The recording duration is determined dynamically by the depth and feature richness of the project. Whether a project requires 45 seconds, 90 seconds, or 2+ minutes to showcase every single model and capability, it must be given as much time as necessary.
- **100% Feature Inventory Coverage**: Every tab, sub-view, model, parameter control, data visualizer, and simulation module must be visited and demonstrated **one by one**.

---

## 2. Mandatory Exploration Rules

### Rule 1: Sequential One-by-One Feature & Model Traversal
- **Exhaustive Navigation**: Sequentially click through every single tab, sub-page, model selector, and navigation view on the platform (`.stTabs`, `[role="tab"]`, `.tab-btn`, `nav a`).
- **Dedicated Demonstration Dwell**: Spend **3.0 to 5.0 seconds** on each individual view or model state so viewers, recruiters, and engineering leaders can absorb the layout, read the metrics, and observe data changes.
- **Never Cut Corners**: Do not skip secondary or technical tabs (such as SHAP feature importance, model architectures, confusion matrices, or raw data views). Every section must be shown.

### Rule 2: Complete Interactive Control & Model Execution
- **Parameter Variation**: Identify and interact with form inputs, sliders, and dropdown selectors (`<select>`, `input[type="number"]`, range sliders), demonstrating model reactivity to changed inputs.
- **Trigger Every Primary Action**: Locate and trigger all available action buttons (`"Predict"`, `"Run Inference"`, `"Calculate"`, `"Simulate"`, `"Apply Mask"`, `"Blended Overlay"`, `"3D / Isometric View"`).
- **Animation & Calculation Stabilization**: When an action is triggered, wait **3 to 5 seconds** for WebGL maps, ApexCharts, Plotly graphs, or backend inference results to fully compute and render before moving to the next element.

### Rule 3: Natural, Cinematic & Full-Page Scrolling Dynamics
- **Full Page Depth Tour**: Incrementally scroll down across the entire vertical height of the page to exhibit lower metric cards, deep learning architecture diagrams, benchmarks, and data tables.
- **Humanized Incremental Wheel Movement**: Use smooth incremental wheel steps (`mouse.wheel(0, 250..350)`) with natural pauses (800ms–1200ms) between scroll movements.
- **Dedicated Chart Inspection**: Whenever a chart, map, or thermal visualization comes into view, pause scrolling for at least 3 seconds.
- **Graceful Bi-Directional Pan**: After reaching the footer/lowest section, smoothly return the page to the top overview banner before terminating the recording.

### Rule 4: Visual Animated Pointer Simulation
- **Visible Pointer Overlay**: A high-contrast animated cursor must be injected directly into the DOM (`playwright-demo-cursor`).
- **Humanized Curved Trajectories**: The mouse must glide across screen coordinates in interpolated steps (8–12 interpolation frames per movement) rather than snapping instantaneously.
- **Click Feedback**: The pointer must visually pulse (scaling from 1.0x to 1.6x and transitioning to bright green) on `mousedown`/`mouseup` to clearly signal user clicks to video viewers.

### Rule 5: Heavy Visual, WebGL & Canvas Rendering Buffer
- **Map & Canvas Wait**: WebGL, Mapbox, Leaflet, and Three.js canvases must be allowed a minimum 3-second stabilization buffer after tab switching to finish vector tile and texture rendering.
- **Chart Animation Buffer**: ApexCharts, Chart.js, and Plotly animations must be given sufficient time to complete their transition animations before mouse scrolling resumes.

### Rule 6: Destructive Action Exclusion
- **Blacklisted Selectors**: Never click elements with text matching `"Reset"`, `"Delete"`, `"Drop"`, `"Sign Out"`, `"Log Out"`, `"Cancel"`, or outbound external links that navigate away from the project domain.

### Rule 7: Dynamic Pacing & Export Standards
- **Recording Duration**: Dynamic and unbounded. Scaled directly to the number of interactive features ($N_{\text{tabs}} \times 4\text{s} + N_{\text{actions}} \times 4\text{s} + \text{scroll tour}$).
- **Video Post-Processing**:
  - Programmatically trim the first **2.0 seconds** of blank loading/DNS resolution.
  - Apply an acceleration factor of **1.15x to 1.20x** to keep movement crisp and engaging without rushing complex charts.
  - Export in standard LinkedIn-compatible format (H.264 codec `libx264`, `yuv420p` pixel format).

---

## 3. Architecture Flow

```text
+---------------------------------------------------------------------------------+
| 1. Launch Project Application (Localhost or Live Vercel Deployment)             |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 2. Inject High-Contrast Animated Visual Cursor (tracks & pulses on click)       |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 3. Exhaustive Feature & Model Discovery                                         |
|    - Discover all tabs, navigation links, and model views                       |
|    - Identify action buttons ("Predict", "Overlay", "Mask", "Calculate")        |
|    - Detect inputs, sliders, and parameter controls                             |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 4. Sequential One-by-One Feature Tour (UNBOUNDED DURATION)                      |
|    - Visit View 1 -> interact controls -> dwell 3-5s                            |
|    - Visit View 2 -> trigger model -> inspect results -> dwell 3-5s             |
|    - Visit View N -> switch perspective -> dwell 3-5s                           |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 5. Comprehensive Full-Depth Page Scroll & Chart Tour                            |
|    - Incremental scroll through all architecture diagrams, metrics, & plots     |
|    - Smooth return to top dashboard hero                                        |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 6. Video Export (MoviePy H.264 MP4, 1.18x Pacing)                               |
+---------------------------------------------------------------------------------+
```

---

## 4. Summary Checklist
- [x] No rigid time limits — duration naturally accommodates the full project.
- [x] Every tab, view, and model selector opened and demonstrated one by one.
- [x] All action buttons clicked with real results displayed.
- [x] Animated pointer guides the viewer's eye across the UI.
- [x] Full page height smoothly scrolled and inspected.
- [x] Exported in high-definition LinkedIn-ready MP4.
