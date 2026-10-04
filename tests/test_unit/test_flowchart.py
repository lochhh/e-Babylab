"""Unit tests for experiments/flowchart.py."""

import pytest

from experiments.flowchart import list_flowchart


@pytest.fixture
def structure(
    listitem_factory,
    outerblock_factory,
    blockitem_factory,
    trialitem_factory,
    attention_getter_factory,
):
    """List → Outer → Block(T1, T2) + Block 'AG block'(AG); T1 → AG when dwell < 500."""
    listitem = listitem_factory()
    outer = outerblock_factory(listitem=listitem, outer_block_name="Fam")
    block = blockitem_factory(outerblock=outer, label="Main")
    t1 = trialitem_factory(blockitem=block, label="T1", position=1)
    t2 = trialitem_factory(blockitem=block, label="T2", code="C2", position=2)
    ag = attention_getter_factory(t1, label="AG", min_dwell_time=500)
    return listitem, outer, block, ag.blockitem, t1, t2, ag


@pytest.mark.django_db
def test_flowchart_structure(structure):
    """Subgraphs per block, order edges, and a dashed attention getter edge."""
    listitem, outer, block, ag_block, t1, t2, ag = structure
    src = list_flowchart(listitem)
    assert src.startswith("flowchart TD")
    assert f'subgraph O{outer.pk}["Outer: Fam"]' in src
    assert f'subgraph B{block.pk}["Block: Main"]' in src
    assert f"T{t1.pk} --> T{t2.pk}" in src
    assert f"B{block.pk} --> B{ag_block.pk}" in src
    assert f'T{t1.pk} -.->|"dwell #60; 500 ms"| T{ag.pk}' in src
    assert f'T{ag.pk}(["AG"])' in src
    assert f"class T{ag.pk} ag" in src


@pytest.mark.django_db
def test_flowchart_cell_target_in_edge_label(structure):
    """A CELL target is shown on the edge."""
    listitem, *_, t1, _t2, _ag = structure
    t1.dwell_target_type, t1.dwell_target_row, t1.dwell_target_col = "CELL", 1, 1
    t1.save()
    assert "in cell (1,1)" in list_flowchart(listitem)


@pytest.mark.django_db
def test_flowchart_randomised_block_has_no_order_edges(structure):
    """Randomised trials are labelled and not chained."""
    listitem, _, block, _, t1, t2, _ = structure
    block.randomise_trials = True
    block.save()
    src = list_flowchart(listitem)
    assert "Block: Main (randomised)" in src
    assert f"T{t1.pk} --> T{t2.pk}" not in src


@pytest.mark.django_db
def test_flowchart_escapes_labels(structure):
    """Researcher text can't break Mermaid syntax."""
    listitem, *_, t2, _ = structure
    t2.label = 'a"]; x'
    t2.save()
    src = list_flowchart(listitem)
    assert 'a"]' not in src
    assert "a#34;#93;#59; x" in src


@pytest.mark.django_db
def test_flowchart_empty_list(listitem_factory):
    """A list without blocks renders a placeholder node."""
    assert "No trials yet" in list_flowchart(listitem_factory())
