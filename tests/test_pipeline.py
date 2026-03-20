from app import make_report_pdf, parse_upload, pes_png, run_pipeline

XYZ = b"""3
Water
O 0.000 0.000 0.000
H 0.758 0.000 0.504
H -0.758 0.000 0.504
"""


def test_parse_xyz_and_run_pipeline():
    molecule = parse_upload("water.xyz", XYZ)
    result = run_pipeline(molecule)

    assert molecule.input_kind == "xyz"
    assert len(molecule.atoms) == 3
    assert result.properties.formula == "H2O"
    assert result.properties.stable_states >= 1
    assert any(point.state == "minimum" for point in result.scan)
    assert "Optimized geometry" in result.optimized_xyz


def test_binary_exports_and_image_warning():
    image_molecule = parse_upload("molecule.png", b"fake-image-bytes")
    image_result = run_pipeline(image_molecule)
    xyz_result = run_pipeline(parse_upload("water.xyz", XYZ))

    assert image_molecule.input_kind == "image"
    assert image_result.warnings
    assert image_result.structure.bond_lengths
    assert make_report_pdf(xyz_result).startswith(b"%PDF-")
    assert pes_png(xyz_result).startswith(b"\x89PNG\r\n\x1a\n")
