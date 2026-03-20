# AI Molecular Analysis

A **single-file Python application** that turns one molecular upload into an automated analysis dashboard.

## What changed

This version is intentionally packaged as a **single `app.py` file** so the full workflow lives in one place instead of a multi-module package.

## What the app includes

- Drag-and-drop support for `.xyz`, `.pdb`, `.sdf`, and molecule images.
- Automated upload → parse → conformer scan → property generation → dashboard rendering flow.
- Dark scientific dashboard with:
  - 3D molecular viewer
  - PES graph
  - conformer table
  - molecular property cards
  - searchable structural tables
  - AI insights panel
  - downloads for `.xyz`, `.png`, `.pdf`, `.csv`, and `.json`
- Lightweight Python-native exporters for PDF and PNG so the app remains fully Python-based.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
streamlit run app.py
```

## Optional chemistry upgrades

The file is still structured so you can later swap in stronger Python chemistry engines:

- **RDKit** for chemistry-aware parsing and conformer generation
- **ASE** for geometry optimization
- **TorchANI** for ML energies and forces
- a Python OCR / graph-reconstruction model for image-to-molecule recognition

## Current limitations

- Image uploads still use a deterministic Python stub rather than a true vision model.
- The conformer and energy workflow is a deterministic scaffold, not an ab initio or production ML potential.
- Dependency installation could not be verified from package indexes in this environment because of proxy/network restrictions.
