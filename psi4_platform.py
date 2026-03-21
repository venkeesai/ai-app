from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

Mode = Literal["beginner", "expert"]
JobType = Literal["optimize", "energy", "frequency"]

_METHOD_KEYWORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmp2\b", re.IGNORECASE), "MP2"),
    (re.compile(r"\bhf\b|hartree[- ]fock", re.IGNORECASE), "HF"),
    (re.compile(r"\bb3lyp\b", re.IGNORECASE), "B3LYP"),
    (re.compile(r"\bpbe0\b", re.IGNORECASE), "PBE0"),
    (re.compile(r"\bm06-2x\b", re.IGNORECASE), "M06-2X"),
    (re.compile(r"\bwb97x-d\b", re.IGNORECASE), "wB97X-D"),
)

_BASIS_KEYWORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"6[- ]31g\*\*", re.IGNORECASE), "6-31G**"),
    (re.compile(r"6[- ]31g\*", re.IGNORECASE), "6-31G*"),
    (re.compile(r"6[- ]31g", re.IGNORECASE), "6-31G"),
    (re.compile(r"def2[- ]svp", re.IGNORECASE), "def2-SVP"),
    (re.compile(r"def2[- ]tzvp", re.IGNORECASE), "def2-TZVP"),
    (re.compile(r"cc-pvdz", re.IGNORECASE), "cc-pVDZ"),
)

_ALLOWED_SYMBOLS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl",
    "Ar", "K", "Ca", "Br", "I",
}

_JOB_LABELS = {
    "optimize": "a geometry optimization",
    "energy": "a single-point energy calculation",
    "frequency": "a vibrational frequency calculation",
}


class MoleculeValidationError(ValueError):
    """Raised when a molecule file or inline XYZ content is invalid."""


class Psi4ExecutionError(RuntimeError):
    """Raised when a Psi4 run cannot be started or finishes unsuccessfully."""


@dataclass(slots=True)
class MoleculeRecord:
    name: str
    charge: int
    multiplicity: int
    xyz_lines: list[str]
    source: str = "inline"

    @property
    def formula(self) -> str:
        counts: dict[str, int] = {}
        for line in self.xyz_lines:
            symbol = line.split()[0]
            counts[symbol] = counts.get(symbol, 0) + 1
        return "".join(
            f"{symbol}{counts[symbol] if counts[symbol] > 1 else ''}"
            for symbol in sorted(counts)
        )

    def to_psi4_block(self) -> str:
        return f"{self.charge} {self.multiplicity}\n" + "\n".join(self.xyz_lines)


@dataclass(slots=True)
class JobRequest:
    prompt: str
    mode: Mode
    method: str
    basis: str
    job_type: JobType
    charge: int
    multiplicity: int
    confidence: float
    notes: list[str] = field(default_factory=list)
    memory: str = "2 GB"
    threads: int = 4
    scf_type: str = "df"
    e_convergence: float = 1e-8
    d_convergence: float = 1e-8

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class GenerationResult:
    request: JobRequest
    molecule: MoleculeRecord
    psi4_input: str
    explanation: list[str]

    def to_manifest(self, workspace: Path) -> dict:
        return {
            "workspace": str(workspace),
            "request": self.request.to_dict(),
            "molecule": {
                "name": self.molecule.name,
                "charge": self.molecule.charge,
                "multiplicity": self.molecule.multiplicity,
                "formula": self.molecule.formula,
                "source": self.molecule.source,
                "atom_count": len(self.molecule.xyz_lines),
            },
            "explanation": self.explanation,
        }


def _match_first(text: str, options: tuple[tuple[re.Pattern[str], str], ...]) -> str | None:
    for pattern, value in options:
        if pattern.search(text):
            return value
    return None


def interpret_request(prompt: str, mode: Mode = "beginner") -> JobRequest:
    text = prompt.strip()
    notes: list[str] = []

    method = _match_first(text, _METHOD_KEYWORDS) or ("B3LYP" if mode == "beginner" else "HF")
    basis = _match_first(text, _BASIS_KEYWORDS) or ("6-31G*" if mode == "beginner" else "def2-SVP")

    if re.search(r"freq|vibration", text, re.IGNORECASE):
        job_type: JobType = "frequency"
    elif re.search(r"single[- ]point|energy", text, re.IGNORECASE):
        job_type = "energy"
    else:
        job_type = "optimize"

    charge_match = re.search(r"charge\s*(-?\d+)", text, re.IGNORECASE)
    multiplicity_match = re.search(r"multiplicity\s*(\d+)", text, re.IGNORECASE)
    charge = int(charge_match.group(1)) if charge_match else 0
    multiplicity = int(multiplicity_match.group(1)) if multiplicity_match else 1

    confidence = 0.56
    if _match_first(text, _METHOD_KEYWORDS):
        confidence += 0.14
    else:
        notes.append("Method inferred from mode defaults.")
    if _match_first(text, _BASIS_KEYWORDS):
        confidence += 0.14
    else:
        notes.append("Basis set inferred from mode defaults.")
    if charge_match or multiplicity_match:
        confidence += 0.08
    else:
        notes.append("Charge/multiplicity left at neutral singlet defaults.")
    if re.search(r"opt|optimize|energy|freq|vibration", text, re.IGNORECASE):
        confidence += 0.08
    else:
        notes.append("Job type inferred as geometry optimization.")

    return JobRequest(
        prompt=prompt,
        mode=mode,
        method=method,
        basis=basis,
        job_type=job_type,
        charge=charge,
        multiplicity=multiplicity,
        confidence=round(min(confidence, 0.98), 2),
        notes=notes,
    )


def _normalize_xyz_lines(raw: str) -> list[str]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        raise MoleculeValidationError("No XYZ content was provided.")

    if lines[0].isdigit():
        expected = int(lines[0])
        payload = lines[2:]
        if len(payload) != expected:
            raise MoleculeValidationError(
                f"XYZ atom count mismatch: header says {expected}, but {len(payload)} coordinate lines were found."
            )
    else:
        payload = lines

    normalized: list[str] = []
    for index, line in enumerate(payload, start=1):
        parts = line.split()
        if len(parts) != 4:
            raise MoleculeValidationError(f"Line {index} is not valid XYZ: {line!r}")
        if parts[0] not in _ALLOWED_SYMBOLS:
            raise MoleculeValidationError(f"Unsupported element symbol {parts[0]!r} on line {index}.")
        for coord in parts[1:]:
            float(coord)
        normalized.append("  ".join([parts[0], *parts[1:]]))
    return normalized


def load_xyz(path: Path, *, name: str | None = None, charge: int = 0, multiplicity: int = 1) -> MoleculeRecord:
    return MoleculeRecord(
        name=name or path.stem,
        charge=charge,
        multiplicity=multiplicity,
        xyz_lines=_normalize_xyz_lines(path.read_text()),
        source=str(path),
    )


def molecule_from_xyz_text(raw: str, *, name: str, charge: int = 0, multiplicity: int = 1) -> MoleculeRecord:
    return MoleculeRecord(
        name=name,
        charge=charge,
        multiplicity=multiplicity,
        xyz_lines=_normalize_xyz_lines(raw),
        source="inline",
    )


def build_psi4_input(request: JobRequest, molecule: MoleculeRecord) -> str:
    if request.job_type == "frequency":
        task_line = f"frequency('{request.method}/{request.basis}', return_wfn=True)"
    else:
        task_line = f"{request.job_type}('{request.method}/{request.basis}')"

    return (
        f"memory {request.memory}\n"
        f"set_num_threads({request.threads})\n\n"
        f"molecule {molecule.name} {{\n{molecule.to_psi4_block()}\n}}\n\n"
        f"set {{\n"
        f"  basis {request.basis}\n"
        f"  scf_type {request.scf_type}\n"
        f"  d_convergence {request.d_convergence:.0e}\n"
        f"  e_convergence {request.e_convergence:.0e}\n"
        f"}}\n\n"
        f"{task_line}\n"
    )


def explain_request(request: JobRequest, molecule: MoleculeRecord) -> list[str]:
    return [
        f"The workflow is {_JOB_LABELS[request.job_type]} using {request.method} with the {request.basis} basis.",
        f"The molecule {molecule.name} is treated as charge {request.charge} and multiplicity {request.multiplicity}.",
        "SCF thresholds are written explicitly so the run stays reproducible and auditable.",
        "No results are fabricated here: this tool only prepares transparent Psi4 inputs and run metadata.",
    ]


def create_generation_result(prompt: str, molecule: MoleculeRecord, *, mode: Mode = "beginner") -> GenerationResult:
    request = interpret_request(prompt, mode=mode)
    request.charge = molecule.charge
    request.multiplicity = molecule.multiplicity
    psi4_input = build_psi4_input(request, molecule)
    explanation = explain_request(request, molecule)
    return GenerationResult(request=request, molecule=molecule, psi4_input=psi4_input, explanation=explanation)


def create_workspace(prompt: str, molecule: MoleculeRecord, workspace: Path, *, mode: Mode = "beginner") -> GenerationResult:
    workspace.mkdir(parents=True, exist_ok=True)
    result = create_generation_result(prompt, molecule, mode=mode)

    (workspace / "request.txt").write_text(prompt.strip() + "\n")
    (workspace / "input.dat").write_text(result.psi4_input)
    (workspace / "explanation.md").write_text("\n".join(f"- {line}" for line in result.explanation) + "\n")
    (workspace / "molecule.xyz").write_text(
        f"{len(molecule.xyz_lines)}\n{molecule.name}\n" + "\n".join(molecule.xyz_lines) + "\n"
    )

    manifest = result.to_manifest(workspace)
    manifest["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    (workspace / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return result


def run_psi4(input_path: Path, output_path: Path, *, psi4_command: str = "psi4") -> subprocess.CompletedProcess[str]:
    executable = shutil.which(psi4_command)
    if executable is None:
        raise Psi4ExecutionError(
            f"Psi4 executable {psi4_command!r} was not found on PATH. Install Psi4 to run the generated input."
        )

    completed = subprocess.run(
        [executable, str(input_path), str(output_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise Psi4ExecutionError(completed.stderr or completed.stdout or "Psi4 returned a non-zero exit code.")
    return completed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Single-file Psi4 workflow generator.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--prompt", required=True, help="Natural-language chemistry request.")
    common.add_argument("--mode", choices=["beginner", "expert"], default="beginner")
    common.add_argument("--xyz-file", type=Path, help="Path to an XYZ file.")
    common.add_argument("--xyz-text", help="Inline XYZ content.")
    common.add_argument("--name", default="sample")
    common.add_argument("--charge", type=int, default=0)
    common.add_argument("--multiplicity", type=int, default=1)

    generate = subparsers.add_parser("generate", parents=[common], help="Generate a reproducible Psi4 workspace.")
    generate.add_argument("--workspace", type=Path, default=Path("runs/latest"))

    subparsers.add_parser("explain", parents=[common], help="Explain the interpreted request and print JSON.")

    run = subparsers.add_parser("run", parents=[common], help="Generate a workspace and execute Psi4 if installed.")
    run.add_argument("--workspace", type=Path, default=Path("runs/latest"))
    run.add_argument("--psi4-command", default="psi4")

    subparsers.add_parser("self-test", help="Run built-in unit tests.")
    return parser


def _load_molecule_from_args(args: argparse.Namespace) -> MoleculeRecord:
    if bool(getattr(args, "xyz_file", None)) == bool(getattr(args, "xyz_text", None)):
        raise SystemExit("Provide exactly one of --xyz-file or --xyz-text.")
    if args.xyz_file:
        return load_xyz(args.xyz_file, name=args.name, charge=args.charge, multiplicity=args.multiplicity)
    return molecule_from_xyz_text(args.xyz_text, name=args.name, charge=args.charge, multiplicity=args.multiplicity)


class BuiltInTests(unittest.TestCase):
    def test_interpret_request_extracts_common_settings(self) -> None:
        request = interpret_request(
            "Optimize this molecule using DFT B3LYP/6-31G* with charge 0 multiplicity 1",
            mode="beginner",
        )
        self.assertEqual(request.method, "B3LYP")
        self.assertEqual(request.basis, "6-31G*")
        self.assertEqual(request.job_type, "optimize")
        self.assertEqual(request.charge, 0)
        self.assertEqual(request.multiplicity, 1)

    def test_xyz_validation_rejects_bad_header(self) -> None:
        with self.assertRaises(MoleculeValidationError):
            molecule_from_xyz_text("2\ncomment\nH 0 0 0\n", name="broken")

    def test_workspace_generation_writes_manifest_and_input(self) -> None:
        molecule = molecule_from_xyz_text(
            "3\nwater\nO 0.000000 0.000000 0.117790\nH 0.000000 0.755453 -0.471161\nH 0.000000 -0.755453 -0.471161\n",
            name="water",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "water-run"
            result = create_workspace(
                "Compute vibrational frequencies with PBE0/def2-SVP for a neutral singlet.",
                molecule,
                workspace,
                mode="expert",
            )
            self.assertTrue((workspace / "input.dat").exists())
            self.assertIn("frequency('PBE0/def2-SVP'", (workspace / "input.dat").read_text())
            manifest = json.loads((workspace / "manifest.json").read_text())
            self.assertEqual(manifest["molecule"]["formula"], "H2O")
            self.assertEqual(result.request.job_type, "frequency")


def run_self_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BuiltInTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "self-test":
        raise SystemExit(run_self_tests())

    molecule = _load_molecule_from_args(args)

    if args.command == "generate":
        result = create_workspace(args.prompt, molecule, args.workspace, mode=args.mode)
        print(json.dumps(result.to_manifest(args.workspace), indent=2))
        print(f"\nWorkspace written to {args.workspace}")
        return

    if args.command == "explain":
        result = create_generation_result(args.prompt, molecule, mode=args.mode)
        payload = {
            "request": result.request.to_dict(),
            "molecule": {"name": result.molecule.name, "formula": result.molecule.formula},
            "explanation": result.explanation,
            "psi4_input": result.psi4_input,
        }
        print(json.dumps(payload, indent=2))
        return

    if args.command == "run":
        create_workspace(args.prompt, molecule, args.workspace, mode=args.mode)
        input_path = args.workspace / "input.dat"
        output_path = args.workspace / "output.out"
        try:
            run_psi4(input_path, output_path, psi4_command=args.psi4_command)
        except Psi4ExecutionError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"Psi4 run completed. Output written to {output_path}")
        return

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
