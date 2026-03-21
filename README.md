# Psi4 Platform (Single Python File)

This repository now provides the Psi4 workflow generator as **one file: `psi4_platform.py`**.

The script turns natural-language chemistry requests into transparent, reproducible Psi4 workspaces while keeping everything in a single Python source file.

## What is inside `psi4_platform.py`

- request parsing for methods, basis sets, job type, charge, and multiplicity
- XYZ molecule validation and loading
- Psi4 input generation
- explanation text for reproducibility
- workspace creation (`input.dat`, `manifest.json`, `request.txt`, `molecule.xyz`, `explanation.md`)
- optional Psi4 execution through `subprocess`
- built-in self-tests via a CLI command

## Usage

### Explain a request

```bash
python psi4_platform.py explain \
  --prompt "Optimize this water molecule using DFT B3LYP/6-31G*" \
  --xyz-file examples/water.xyz \
  --name water
```

### Generate a workspace

```bash
python psi4_platform.py generate \
  --prompt "Compute vibrational frequencies with PBE0/def2-SVP for a neutral singlet" \
  --xyz-file examples/water.xyz \
  --name water \
  --workspace runs/water
```

### Run Psi4 if installed

```bash
python psi4_platform.py run \
  --prompt "Run a single-point MP2/cc-pVDZ energy" \
  --xyz-file examples/water.xyz \
  --name water \
  --workspace runs/water-mp2
```

### Run built-in tests

```bash
python psi4_platform.py self-test
```
