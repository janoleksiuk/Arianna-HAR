# Arianna-HAR
Human activity recognition by reasoning with a network of ontologies for assistive robotic systems, based on the Arianna+ framework.

## Overview
This repository is a symbolic prototype of an ontology-network pipeline for human activity recognition and robot assistance. It uses an event-driven scheduler to connect perception, ontology updates, action recognition, early intent prediction, and robot task dispatch. The default setup is fully simulated: a pose detector generates pose labels and a robot interface logs its actions.

## Features
- Event-driven execution pipeline (Arianna+-style).
- Ontology-inspired state updates and action recognition.
- Early intent detection with action families and pre-tasks.
- Trace logging to JSONL for analysis or dashboards.
- Architecture diagram export (DOT and optional SVG).

## Project layout
- `main.py`: entry point that wires the scheduler, procedures, and simulation loop.
- `config.py`: system configuration (actions, tasks, tracing, diagram export).
- `ontologies/`: symbolic ontologies and memory store.
- `procedures/`: event-driven procedures for U/P/S/A/R stages.
- `perception/`: simulated pose detector.
- `robot/`: simulated robot behaviors and interface.
- `scheduler.py`: event scheduler and trace sink.
- `visualization/`: architecture diagram builder and a trace dashboard.

## Quick start
1. Run the system:
   ```bash
   python main.py
   ```
2. The run produces trace output and (by default) an architecture diagram:
   - `runs/trace.jsonl`
   - `runs/diagrams/architecture.dot`
   - `runs/diagrams/architecture.svg` (requires Graphviz `dot`)

## Configuration
Adjust behavior in `config.py`, including:
- `POSE_DETECTOR_MODE` for random vs action-sequence generation.
- `ACTION_DEFINITIONS` and `TASK_DEFINITIONS` for domain vocabulary.
- `TRACE_JSONL*` for trace capture.
- `ARCH_DIAGRAM_*` for diagram export.

## Trace dashboard (optional)
The Streamlit app reads `runs/trace.jsonl` and provides filters and plots.

```bash
streamlit run visualization/dashboard/app.py
```

Dependencies for the dashboard include `streamlit`, `pandas`, and `plotly`.


