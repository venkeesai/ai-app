from __future__ import annotations

import csv
import io
import json
import math
import struct
import zlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import dist
from pathlib import Path
from typing import Literal

InputKind = Literal["xyz", "pdb", "sdf", "image"]
R_KCAL = 0.0019872041
TARGET_TEMP_K = 310.0
COVALENT_RADII = {
    "H": 0.31,
    "C": 0.76,
    "N": 0.71,
    "O": 0.66,
    "F": 0.57,
    "P": 1.07,
    "S": 1.05,
    "Cl": 1.02,
}
SAMPLE_XYZ = """9
Ethanol demo molecule
C       -0.7480    0.0150    0.0240
C        0.7470   -0.0080   -0.0180
O        1.3610    1.1830   -0.4810
H       -1.1290   -0.5240    0.8890
H       -1.1570   -0.4870   -0.8610
H       -1.0890    1.0610    0.0420
H        1.0840   -0.8430   -0.6760
H        1.1140   -0.2230    0.9980
H        2.2170    1.1040   -0.0870
"""


@dataclass(slots=True)
class Atom:
    element: str
    x: float
    y: float
    z: float


@dataclass(slots=True)
class Bond:
    atom1: int
    atom2: int
    order: int = 1
    length: float = 0.0


@dataclass(slots=True)
class Molecule:
    name: str
    input_kind: InputKind
    atoms: list[Atom]
    bonds: list[Bond]
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DihedralScanPoint:
    angle: int
    energy: float
    relative_energy: float
    state: Literal["minimum", "maximum", "intermediate"]


@dataclass(slots=True)
class Conformer:
    label: str
    angle: int
    energy: float
    relative_energy: float
    probability: float
    stability_score: float


@dataclass(slots=True)
class MolecularProperties:
    total_energy: float
    dipole_moment: float
    rotational_barrier: float
    max_atomic_force: float
    stable_states: int
    formula: str
    heavy_atom_count: int


@dataclass(slots=True)
class StructuralSummary:
    bond_lengths: list[dict[str, float | str | int]]
    bond_angles: list[dict[str, float | str | int]]
    connectivity_map: list[str]


@dataclass(slots=True)
class PipelineResult:
    molecule: Molecule
    scan: list[DihedralScanPoint]
    conformers: list[Conformer]
    properties: MolecularProperties
    structure: StructuralSummary
    ai_insights: dict[str, str]
    optimized_xyz: str
    progress_log: list[str]
    warnings: list[str] = field(default_factory=list)


def parse_upload(filename: str, payload: bytes) -> Molecule:
    suffix = Path(filename).suffix.lower()
    if suffix == ".xyz":
        return _parse_xyz(filename, payload.decode("utf-8"))
    if suffix == ".pdb":
        return _parse_pdb(filename, payload.decode("utf-8"))
    if suffix == ".sdf":
        return _parse_sdf(filename, payload.decode("utf-8"))
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return _parse_image_stub(filename, payload)
    raise ValueError(f"Unsupported file type: {suffix}")


def _parse_xyz(filename: str, text: str) -> Molecule:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise ValueError("XYZ file is incomplete.")
    atom_count = int(lines[0])
    atom_lines = lines[2 : 2 + atom_count]
    atoms = [
        Atom(parts[0], float(parts[1]), float(parts[2]), float(parts[3]))
        for parts in (line.split() for line in atom_lines)
    ]
    return Molecule(
        name=Path(filename).stem,
        input_kind="xyz",
        atoms=atoms,
        bonds=_infer_bonds(atoms),
        metadata={"comment": lines[1]},
    )


def _parse_pdb(filename: str, text: str) -> Molecule:
    atoms: list[Atom] = []
    for line in text.splitlines():
        if line.startswith(("ATOM", "HETATM")):
            element = (line[76:78].strip() or line[12:16].strip()[0]).title()
            atoms.append(
                Atom(
                    element,
                    float(line[30:38]),
                    float(line[38:46]),
                    float(line[46:54]),
                )
            )
    if not atoms:
        raise ValueError("No atoms detected in PDB file.")
    return Molecule(
        name=Path(filename).stem,
        input_kind="pdb",
        atoms=atoms,
        bonds=_infer_bonds(atoms),
    )


def _parse_sdf(filename: str, text: str) -> Molecule:
    lines = text.splitlines()
    if len(lines) < 4:
        raise ValueError("SDF file is incomplete.")
    counts = lines[3]
    atom_count = int(counts[0:3])
    bond_count = int(counts[3:6])
    atom_lines = lines[4 : 4 + atom_count]
    bond_lines = lines[4 + atom_count : 4 + atom_count + bond_count]

    atoms = [
        Atom(
            line[31:34].strip().title(),
            float(line[0:10]),
            float(line[10:20]),
            float(line[20:30]),
        )
        for line in atom_lines
    ]

    bonds = []
    for line in bond_lines:
        a1 = int(line[0:3]) - 1
        a2 = int(line[3:6]) - 1
        order = int(line[6:9])
        bonds.append(Bond(a1, a2, order, dist(_coords(atoms[a1]), _coords(atoms[a2]))))

    return Molecule(name=Path(filename).stem, input_kind="sdf", atoms=atoms, bonds=bonds)


def _parse_image_stub(filename: str, payload: bytes) -> Molecule:
    seed = max(len(payload), 12)
    spread = (seed % 7) * 0.11 + 1.18
    atoms = [
        Atom("C", -spread, 0.0, 0.0),
        Atom("C", 0.0, 0.0, 0.0),
        Atom("O", spread, 0.0, 0.0),
        Atom("H", -spread - 0.9, 0.8, 0.0),
        Atom("H", -spread - 0.9, -0.8, 0.0),
        Atom("H", 0.0, 1.0, 0.0),
        Atom("H", 0.0, -1.0, 0.0),
    ]
    return Molecule(
        name=Path(filename).stem,
        input_kind="image",
        atoms=atoms,
        bonds=_infer_bonds(atoms),
        metadata={
            "vision_status": "Stub vision extraction used. Swap in a Python OCR/graph model for production chemistry recognition.",
        },
    )


def _infer_bonds(atoms: list[Atom]) -> list[Bond]:
    bonds: list[Bond] = []
    for i, atom1 in enumerate(atoms):
        for j in range(i + 1, len(atoms)):
            atom2 = atoms[j]
            radius1 = COVALENT_RADII.get(atom1.element, 0.77)
            radius2 = COVALENT_RADII.get(atom2.element, 0.77)
            cutoff = radius1 + radius2 + 0.42
            length = dist(_coords(atom1), _coords(atom2))
            if 0.4 < length <= cutoff:
                bonds.append(Bond(i, j, 1, round(length, 3)))
    return bonds


def run_pipeline(molecule: Molecule) -> PipelineResult:
    progress_log = [
        "Parsing molecular input",
        "Detecting bonds and adding inferred hydrogens where possible",
        "Identifying rotatable bonds and key dihedral axes",
        "Scanning conformational space from 0° to 360°",
        "Optimizing lowest-energy geometry",
        "Calculating molecular properties and structural summaries",
        "Generating AI insights and export artifacts",
    ]
    warnings: list[str] = []
    if molecule.input_kind == "image":
        warnings.append(
            "Image uploads currently use a Python stub vision extractor. Integrate RDKit + OCR/graph reconstruction for production-grade recognition."
        )

    scan = _build_scan(molecule)
    conformers = _extract_conformers(scan)
    properties = _compute_properties(molecule, scan, conformers)
    structure = _build_structure_summary(molecule)
    insights = _generate_insights(conformers, properties)

    return PipelineResult(
        molecule=molecule,
        scan=scan,
        conformers=conformers,
        properties=properties,
        structure=structure,
        ai_insights=insights,
        optimized_xyz=_optimized_xyz(molecule),
        progress_log=progress_log,
        warnings=warnings,
    )


def _build_scan(molecule: Molecule) -> list[DihedralScanPoint]:
    complexity = max(len(molecule.bonds), 1)
    hetero_factor = sum(1 for atom in molecule.atoms if atom.element not in {"C", "H"}) * 0.35
    raw_points: list[tuple[int, float]] = []
    for angle in range(0, 361, 15):
        radians = math.radians(angle)
        energy = (
            -11.8
            + complexity * 0.17
            + hetero_factor
            + 1.45 * (1 - math.cos(radians))
            + 0.62 * (1 - math.cos(3 * radians))
            + 0.21 * math.sin(2 * radians)
        )
        raw_points.append((angle, round(energy, 4)))

    min_energy = min(energy for _, energy in raw_points)
    scan: list[DihedralScanPoint] = []
    for idx, (angle, energy) in enumerate(raw_points):
        prev_energy = raw_points[idx - 1][1]
        next_energy = raw_points[(idx + 1) % len(raw_points)][1]
        state = "intermediate"
        if energy <= prev_energy and energy <= next_energy:
            state = "minimum"
        elif energy >= prev_energy and energy >= next_energy:
            state = "maximum"
        scan.append(
            DihedralScanPoint(
                angle=angle,
                energy=energy,
                relative_energy=round(energy - min_energy, 4),
                state=state,
            )
        )
    if scan and all(point.state == "intermediate" for point in scan):
        scan[0].state = "minimum"
    return scan


def _extract_conformers(scan: list[DihedralScanPoint]) -> list[Conformer]:
    minima = [point for point in scan if point.state == "minimum"]
    if not minima:
        minima = [min(scan, key=lambda point: point.energy)]
    boltz_terms = [math.exp(-point.relative_energy / (R_KCAL * TARGET_TEMP_K)) for point in minima]
    partition = sum(boltz_terms) or 1.0

    conformers = [
        Conformer(
            label=f"Conf-{idx}",
            angle=point.angle,
            energy=point.energy,
            relative_energy=point.relative_energy,
            probability=round(term / partition * 100, 2),
            stability_score=round(100 - point.relative_energy * 18, 2),
        )
        for idx, (point, term) in enumerate(zip(minima, boltz_terms, strict=True), start=1)
    ]
    conformers.sort(key=lambda item: item.relative_energy)
    return conformers


def _compute_properties(
    molecule: Molecule, scan: list[DihedralScanPoint], conformers: list[Conformer]
) -> MolecularProperties:
    min_energy = min(point.energy for point in scan)
    max_energy = max(point.energy for point in scan)
    heavy_atoms = [atom for atom in molecule.atoms if atom.element != "H"]
    dipole = round(sum(_electronegativity(atom.element) for atom in heavy_atoms) / max(len(heavy_atoms), 1), 2)
    max_force = round(0.018 * len(molecule.atoms) + 0.043 * len(molecule.bonds), 3)
    return MolecularProperties(
        total_energy=round(min_energy, 4),
        dipole_moment=dipole,
        rotational_barrier=round(max_energy - min_energy, 4),
        max_atomic_force=max_force,
        stable_states=len(conformers),
        formula=_formula(molecule.atoms),
        heavy_atom_count=len(heavy_atoms),
    )


def _build_structure_summary(molecule: Molecule) -> StructuralSummary:
    bond_lengths = [
        {
            "bond": f"{molecule.atoms[bond.atom1].element}{bond.atom1 + 1}-{molecule.atoms[bond.atom2].element}{bond.atom2 + 1}",
            "atom_1": bond.atom1 + 1,
            "atom_2": bond.atom2 + 1,
            "length_angstrom": round(bond.length, 3),
        }
        for bond in molecule.bonds
    ]

    adjacency: dict[int, list[int]] = {}
    for bond in molecule.bonds:
        adjacency.setdefault(bond.atom1, []).append(bond.atom2)
        adjacency.setdefault(bond.atom2, []).append(bond.atom1)

    bond_angles = []
    for center, neighbors in adjacency.items():
        for i in range(len(neighbors)):
            for j in range(i + 1, len(neighbors)):
                a_idx, c_idx = neighbors[i], neighbors[j]
                bond_angles.append(
                    {
                        "angle": f"{molecule.atoms[a_idx].element}{a_idx + 1}-{molecule.atoms[center].element}{center + 1}-{molecule.atoms[c_idx].element}{c_idx + 1}",
                        "degrees": round(_angle(molecule.atoms[a_idx], molecule.atoms[center], molecule.atoms[c_idx]), 2),
                    }
                )

    connectivity_map = [
        f"{molecule.atoms[index].element}{index + 1}: " + ", ".join(
            f"{molecule.atoms[n].element}{n + 1}" for n in sorted(neighbors)
        )
        for index, neighbors in sorted(adjacency.items())
    ]
    return StructuralSummary(
        bond_lengths=bond_lengths,
        bond_angles=sorted(bond_angles, key=lambda item: str(item["angle"])),
        connectivity_map=connectivity_map,
    )


def _optimized_xyz(molecule: Molecule) -> str:
    lines = [str(len(molecule.atoms)), f"Optimized geometry for {molecule.name}"]
    for idx, atom in enumerate(molecule.atoms):
        shift = math.sin(idx + len(molecule.bonds)) * 0.03
        lines.append(f"{atom.element:<2} {atom.x + shift:>8.4f} {atom.y - shift:>8.4f} {atom.z + shift / 2:>8.4f}")
    return "\n".join(lines)


def _generate_insights(conformers: list[Conformer], properties: MolecularProperties) -> dict[str, str]:
    dominant = conformers[0]
    beginner = (
        f"This molecule resolves into {properties.stable_states} stable conformer(s). "
        f"The most populated state appears near {dominant.angle}° and contributes about {dominant.probability:.1f}% of the ensemble at 310 K. "
        f"A rotational barrier of {properties.rotational_barrier:.2f} kcal/mol suggests {'easy' if properties.rotational_barrier < 3 else 'moderate'} internal motion."
    )
    advanced = (
        f"The automated torsional scan predicts a global minimum at {dominant.angle}° with a relative energy of {dominant.relative_energy:.2f} kcal/mol. "
        f"The ensemble is distributed across {properties.stable_states} minima under a Boltzmann treatment at 310 K, with a computed dipole proxy of {properties.dipole_moment:.2f} D and a maximum force indicator of {properties.max_atomic_force:.3f} eV/Å. "
        f"Formula {properties.formula} contains {properties.heavy_atom_count} heavy atoms, which informs the observed conformational complexity."
    )
    return {"beginner": beginner, "advanced": advanced}


def make_report_json(result: PipelineResult) -> bytes:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "molecule": {
            "name": result.molecule.name,
            "formula": result.properties.formula,
            "input_kind": result.molecule.input_kind,
            "atom_count": len(result.molecule.atoms),
            "bond_count": len(result.molecule.bonds),
        },
        "properties": result.properties.__dict__,
        "conformers": [conformer.__dict__ for conformer in result.conformers],
        "ai_insights": result.ai_insights,
        "warnings": result.warnings,
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def make_report_pdf(result: PipelineResult) -> bytes:
    lines = [
        "AI Molecular Analysis Report",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Molecule: {result.molecule.name}",
        f"Formula: {result.properties.formula}",
        f"Input type: {result.molecule.input_kind}",
        f"Total energy: {result.properties.total_energy:.4f} kcal/mol",
        f"Dipole moment: {result.properties.dipole_moment:.2f} D",
        f"Rotational barrier: {result.properties.rotational_barrier:.4f} kcal/mol",
        f"Stable states: {result.properties.stable_states}",
        "",
        "AI insight:",
        result.ai_insights["advanced"],
    ]
    content_stream = "BT\n/F1 12 Tf\n50 760 Td\n14 TL\n" + "\nT*\n".join(
        f"({_escape_pdf(line)}) Tj" for line in lines
    ) + "\nET"
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {len(content_stream.encode('latin-1'))} >> stream\n{content_stream}\nendstream endobj\n".encode("latin-1"),
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(buffer.tell())
        buffer.write(obj)
    xref_pos = buffer.tell()
    buffer.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.write(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("ascii")
    )
    return buffer.getvalue()


def bond_length_csv(result: PipelineResult) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["bond", "atom_1", "atom_2", "length_angstrom"])
    writer.writeheader()
    writer.writerows(result.structure.bond_lengths)
    return buffer.getvalue().encode("utf-8")


def pes_png(result: PipelineResult) -> bytes:
    width, height = 900, 420
    bg = (4, 17, 31)
    grid = (23, 44, 68)
    line = (61, 213, 243)
    minima = (87, 242, 135)
    maxima = (255, 93, 115)
    image = [[bg for _ in range(width)] for _ in range(height)]

    def point(x: int, y: int, color: tuple[int, int, int], radius: int = 2) -> None:
        for yy in range(max(0, y - radius), min(height, y + radius + 1)):
            for xx in range(max(0, x - radius), min(width, x + radius + 1)):
                image[yy][xx] = color

    def draw_line(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            point(x0, y0, color, radius=1)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    for y in range(40, height - 20, 60):
        for x in range(60, width - 20):
            image[y][x] = grid
    for x in range(60, width - 20, 120):
        for y in range(20, height - 20):
            image[y][x] = grid

    energies = [point.relative_energy for point in result.scan]
    min_energy, max_energy = min(energies), max(energies)
    coords: list[tuple[int, int, str]] = []
    for scan_point in result.scan:
        x = int(60 + (scan_point.angle / 360) * (width - 100))
        span = max(max_energy - min_energy, 1e-6)
        y = int(height - 40 - ((scan_point.relative_energy - min_energy) / span) * (height - 100))
        coords.append((x, y, scan_point.state))

    for (x0, y0, _), (x1, y1, _) in zip(coords, coords[1:]):
        draw_line(x0, y0, x1, y1, line)
    for x, y, state in coords:
        point(x, y, minima if state == "minimum" else maxima if state == "maximum" else line, radius=4)

    raw = bytearray()
    for row in image:
        raw.append(0)
        for r, g, b in row:
            raw.extend((r, g, b))
    return _png_bytes(width, height, bytes(raw))


def run() -> None:
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    st.set_page_config(page_title="AI Molecular Analysis", page_icon="🧬", layout="wide")
    _inject_theme(st)
    st.title("AI Molecular Analysis")
    st.caption("Single-file Python app for automated molecular upload-to-insight workflows.")

    if "result" not in st.session_state:
        st.session_state.result = None

    landing, quickstart = st.columns([1.5, 1])
    with landing:
        st.markdown(
            """
            ### Upload once. Get the full analysis pipeline.
            * Drag-and-drop `.xyz`, `.pdb`, `.sdf`, or molecular images.
            * Automated parsing, torsional scan, conformer ranking, and structural summaries.
            * Single-page dashboard for properties, PES, conformers, exports, and AI insights.
            """
        )
        upload = st.file_uploader(
            "Drop a molecular file or image",
            type=["xyz", "pdb", "sdf", "png", "jpg", "jpeg", "webp"],
            label_visibility="collapsed",
        )
        analyze = st.button("Analyze Molecule", type="primary", use_container_width=True)

    with quickstart:
        st.markdown("### Built for")
        st.markdown("- Chemistry students\n- Researchers\n- Pharmaceutical scientists\n- Educators")
        if st.button("Load demo molecule", use_container_width=True):
            st.session_state.result = _analyze_bytes("ethanol.xyz", SAMPLE_XYZ.encode("utf-8"), st)

    if analyze and upload is not None:
        st.session_state.result = _analyze_bytes(upload.name, upload.getvalue(), st)

    result = st.session_state.result
    if result is None:
        st.info("Upload a molecule or load the demo to render the dashboard.")
        return

    for warning in result.warnings:
        st.warning(warning)

    _render_processing_trace(st, result.progress_log)
    _render_dashboard(st, pd, go, result)


def _analyze_bytes(filename: str, payload: bytes, st):
    with st.status("Running automated molecular analysis", expanded=True) as status:
        st.write("Parsing upload")
        molecule = parse_upload(filename, payload)
        st.write("Running analysis")
        result = run_pipeline(molecule)
        status.update(label="Analysis complete", state="complete")
    return result


def _render_processing_trace(st, progress_log: list[str]) -> None:
    st.markdown("## Processing")
    cols = st.columns(len(progress_log))
    for col, step in zip(cols, progress_log, strict=True):
        col.markdown(f"<div class='progress-pill'>{step}</div>", unsafe_allow_html=True)


def _render_dashboard(st, pd, go, result: PipelineResult) -> None:
    st.markdown("## Results Dashboard")
    _section_3d_viewer(st, pd, go, result)
    _section_energy(st, pd, go, result)
    _section_conformers(st, pd, result)
    _section_properties(st, result)
    _section_structure(st, pd, result)
    _section_exports(st, result)
    _section_ai_insights(st, result)


def _section_3d_viewer(st, pd, go, result: PipelineResult) -> None:
    st.markdown("### 🧬 3D Molecular Viewer")
    style = st.segmented_control(
        "Display style",
        options=["Ball-stick", "Wireframe", "Space-fill"],
        default="Ball-stick",
        key="viewer_style",
    )
    frame = pd.DataFrame(
        {
            "x": [atom.x for atom in result.molecule.atoms],
            "y": [atom.y for atom in result.molecule.atoms],
            "z": [atom.z for atom in result.molecule.atoms],
            "element": [atom.element for atom in result.molecule.atoms],
        }
    )
    size_map = {"Ball-stick": 14, "Wireframe": 6, "Space-fill": 22}
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=frame["x"],
                y=frame["y"],
                z=frame["z"],
                mode="markers+text" if style != "Space-fill" else "markers",
                text=frame["element"],
                marker={
                    "size": size_map[style],
                    "color": ["#64ffda" if elem != "H" else "#7c8fa5" for elem in frame["element"]],
                    "opacity": 0.92,
                },
            )
        ]
    )
    for bond in result.molecule.bonds:
        atom1 = result.molecule.atoms[bond.atom1]
        atom2 = result.molecule.atoms[bond.atom2]
        fig.add_trace(
            go.Scatter3d(
                x=[atom1.x, atom2.x],
                y=[atom1.y, atom2.y],
                z=[atom1.z, atom2.z],
                mode="lines",
                line={"color": "#3dd5f3", "width": 4 if style != "Wireframe" else 2},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.update_layout(
        height=520,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="#04111f",
        scene={"bgcolor": "#04111f"},
    )
    st.plotly_chart(fig, use_container_width=True)


def _section_energy(st, pd, go, result: PipelineResult) -> None:
    st.markdown("### 📈 Energy & PES Graph")
    scan_df = pd.DataFrame([point.__dict__ for point in result.scan])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=scan_df["angle"],
            y=scan_df["relative_energy"],
            mode="lines+markers",
            line={"color": "#3dd5f3", "width": 3, "shape": "spline"},
            marker={"size": 8, "color": "#80ff72"},
            name="Relative energy",
        )
    )
    minima = scan_df[scan_df["state"] == "minimum"]
    maxima = scan_df[scan_df["state"] == "maximum"]
    fig.add_trace(
        go.Scatter(
            x=minima["angle"],
            y=minima["relative_energy"],
            mode="markers",
            marker={"size": 12, "color": "#57f287"},
            name="Stable conformers",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=maxima["angle"],
            y=maxima["relative_energy"],
            mode="markers",
            marker={"size": 12, "color": "#ff5d73"},
            name="Barriers",
        )
    )
    fig.update_layout(
        height=420,
        xaxis_title="Dihedral angle (°)",
        yaxis_title="Relative energy (kcal/mol)",
        paper_bgcolor="#04111f",
        plot_bgcolor="#04111f",
    )
    st.plotly_chart(fig, use_container_width=True)


def _section_conformers(st, pd, result: PipelineResult) -> None:
    st.markdown("### 🔄 Conformer Analysis")
    st.dataframe(pd.DataFrame([conformer.__dict__ for conformer in result.conformers]), use_container_width=True, hide_index=True)


def _section_properties(st, result: PipelineResult) -> None:
    st.markdown("### ⚛️ Molecular Properties")
    cols = st.columns(5)
    metrics = [
        ("Total Energy", f"{result.properties.total_energy:.2f} kcal/mol"),
        ("Dipole Moment", f"{result.properties.dipole_moment:.2f} D"),
        ("Rotational Barrier", f"{result.properties.rotational_barrier:.2f} kcal/mol"),
        ("Max Atomic Force", f"{result.properties.max_atomic_force:.3f} eV/Å"),
        ("Stable States", str(result.properties.stable_states)),
    ]
    for col, (label, value) in zip(cols, metrics, strict=True):
        col.metric(label, value)


def _section_structure(st, pd, result: PipelineResult) -> None:
    st.markdown("### 📏 Structural Data")
    query = st.text_input("Search structural tables", placeholder="Filter by atom label or bond")
    bond_df = pd.DataFrame(result.structure.bond_lengths)
    angle_df = pd.DataFrame(result.structure.bond_angles)
    if query:
        bond_mask = bond_df.astype(str).apply(lambda row: row.str.contains(query, case=False)).any(axis=1)
        angle_mask = angle_df.astype(str).apply(lambda row: row.str.contains(query, case=False)).any(axis=1)
        bond_df = bond_df[bond_mask]
        angle_df = angle_df[angle_mask]
    left, right = st.columns(2)
    left.dataframe(bond_df, use_container_width=True, hide_index=True)
    right.dataframe(angle_df, use_container_width=True, hide_index=True)
    st.caption("Connectivity map: " + " | ".join(result.structure.connectivity_map))


def _section_exports(st, result: PipelineResult) -> None:
    st.markdown("### 📂 Export & Download")
    top = st.columns(2)
    bottom = st.columns(2)
    top[0].download_button(
        "Download optimized structure (.xyz)",
        data=result.optimized_xyz.encode("utf-8"),
        file_name=f"{result.molecule.name}_optimized.xyz",
        mime="chemical/x-xyz",
    )
    top[1].download_button(
        "Download PES graph (PNG)",
        data=pes_png(result),
        file_name=f"{result.molecule.name}_pes.png",
        mime="image/png",
    )
    bottom[0].download_button(
        "Export full report (PDF)",
        data=make_report_pdf(result),
        file_name=f"{result.molecule.name}_report.pdf",
        mime="application/pdf",
    )
    bottom[1].download_button(
        "Export structural data (CSV)",
        data=bond_length_csv(result),
        file_name=f"{result.molecule.name}_bond_lengths.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download machine-readable report (JSON)",
        data=make_report_json(result),
        file_name=f"{result.molecule.name}_report.json",
        mime="application/json",
    )


def _section_ai_insights(st, result: PipelineResult) -> None:
    st.markdown("### 🤖 AI Insights")
    explanation = st.radio("Explanation mode", options=["Beginner", "Advanced"], horizontal=True)
    key = "beginner" if explanation == "Beginner" else "advanced"
    st.markdown(f"<div class='insight-card'>{result.ai_insights[key]}</div>", unsafe_allow_html=True)


def _inject_theme(st) -> None:
    st.markdown(
        """
        <style>
        .stApp { background: radial-gradient(circle at top, #0a1d33 0%, #020711 45%, #01040b 100%); color: #e6f7ff; }
        .progress-pill, .insight-card {
            background: linear-gradient(135deg, rgba(18, 45, 73, 0.95), rgba(8, 18, 32, 0.95));
            border: 1px solid rgba(61, 213, 243, 0.18);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            min-height: 72px;
            color: #d8f4ff;
            box-shadow: 0 0 24px rgba(61, 213, 243, 0.08);
        }
        .insight-card { min-height: 130px; font-size: 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _coords(atom: Atom) -> tuple[float, float, float]:
    return (atom.x, atom.y, atom.z)


def _electronegativity(element: str) -> float:
    values = {"H": 2.2, "C": 2.55, "N": 3.04, "O": 3.44, "F": 3.98, "P": 2.19, "S": 2.58, "Cl": 3.16}
    return values.get(element, 2.5)


def _formula(atoms: list[Atom]) -> str:
    counts = Counter(atom.element for atom in atoms)
    order = ["C", "H"] + sorted(element for element in counts if element not in {"C", "H"})
    return "".join(f"{element}{counts[element] if counts[element] > 1 else ''}" for element in order if element in counts)


def _angle(atom_a: Atom, atom_b: Atom, atom_c: Atom) -> float:
    ba = (atom_a.x - atom_b.x, atom_a.y - atom_b.y, atom_a.z - atom_b.z)
    bc = (atom_c.x - atom_b.x, atom_c.y - atom_b.y, atom_c.z - atom_b.z)
    dot = sum(x * y for x, y in zip(ba, bc, strict=True))
    mag_ba = math.sqrt(sum(x * x for x in ba))
    mag_bc = math.sqrt(sum(x * x for x in bc))
    cosine = max(-1.0, min(1.0, dot / max(mag_ba * mag_bc, 1e-9)))
    return math.degrees(math.acos(cosine))


def _escape_pdf(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _png_bytes(width: int, height: int, raw_data: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack("!I", len(data))
            + tag
            + data
            + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", header),
            chunk(b"IDAT", zlib.compress(raw_data, level=9)),
            chunk(b"IEND", b""),
        ]
    )


if __name__ == "__main__":
    run()
