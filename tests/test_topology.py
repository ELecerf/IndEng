from pathlib import Path

from indeng.config.loader import load_scenario
from indeng.viz.topology import save_topology, topology_dot

ROOT = Path(__file__).resolve().parents[1]


def test_v_topology_shows_divergence():
    scenario = load_scenario(ROOT / "config" / "scenarios" / "v_minimal.yaml")
    dot = topology_dot(scenario)
    assert dot.startswith("digraph")
    assert '"demande" -> "prep"' in dot
    assert '"prep" -> "line_a"' in dot
    assert '"prep" -> "line_b"' in dot
    assert '"line_a" -> "P1"' in dot
    assert '"line_b" -> "P2"' in dot


def test_highlight_marks_bottleneck():
    scenario = load_scenario(ROOT / "config" / "scenarios" / "v_minimal.yaml")
    dot = topology_dot(scenario, highlight="line_b")
    assert "GOULOT" in dot
    assert "#FF6B6B" in dot


def test_a_demo_shows_component_assembly():
    scenario = load_scenario(ROOT / "config" / "scenarios" / "a_demo.yaml")
    dot = topology_dot(scenario)
    assert '"decoupe_a" -> "assemblage"' in dot
    assert '"decoupe_b" -> "assemblage"' in dot
    assert '"decoupe_c" -> "assemblage"' in dot
    assert 'label="comp_a x2.0"' in dot
    assert 'label="comp_c x2.0"' in dot
    assert '"assemblage" -> "P1"' in dot
    assert '"assemblage" -> "P2"' in dot


def test_t_demo_shows_convergence_then_divergence():
    scenario = load_scenario(ROOT / "config" / "scenarios" / "t_demo.yaml")
    dot = topology_dot(scenario)
    assert '"sous_ensemble_a" -> "assemblage"' in dot
    assert '"sous_ensemble_b" -> "assemblage"' in dot
    assert '"assemblage" -> "finition_x"' in dot
    assert '"assemblage" -> "finition_y"' in dot


def test_save_topology_writes_dot(tmp_path):
    scenario = load_scenario(ROOT / "config" / "scenarios" / "v_minimal.yaml")
    paths = save_topology(scenario, tmp_path)
    assert (tmp_path / "topology.dot").exists()
    assert (tmp_path / "topology.dot") in paths
