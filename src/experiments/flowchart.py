"""Read-only Mermaid flowchart of a list's blocks, trials and attention getters."""

import re
from itertools import pairwise

from .models import ListItem, TrialItem

_UNSAFE = re.compile(r"[^\w .,:()'/-]")


def _text(value: str) -> str:
    """Escape text for a quoted Mermaid label using numeric entity codes.

    Args:
        value (str): Researcher-entered text.

    Returns:
        str: Text with unsafe characters replaced by ``#<code>;`` entities.

    """
    return _UNSAFE.sub(lambda m: f"#{ord(m.group())};", value)


def _chain(ids: list[str]) -> list[str]:
    """Return ``a --> b`` edges linking consecutive node ids.

    Args:
        ids (list[str]): Mermaid node ids in order.

    Returns:
        list[str]: One edge line per consecutive pair.

    """
    return [f"  {a} --> {b}" for a, b in pairwise(ids)]


def _dwell_edge(trial: TrialItem) -> str:
    """Return the dashed edge from a trial to its attention getter.

    Args:
        trial (TrialItem): A trial with an attention getter set.

    Returns:
        str: Mermaid edge line labelled with the dwell threshold.

    """
    label = f"dwell < {trial.min_dwell_time} ms"
    if trial.dwell_target is not None:
        label += f" in cell ({trial.dwell_target[0]},{trial.dwell_target[1]})"
    return f'  T{trial.pk} -.->|"{_text(label)}"| T{trial.attention_getter_id}'


def list_flowchart(list_item: ListItem) -> str:
    """Return Mermaid source showing a list's structure as configured.

    Outer and inner blocks are nested subgraphs. Solid arrows follow the
    configured order and are omitted where the order is randomised per
    participant. Attention getters are rounded nodes reached by dashed edges
    labelled with the dwell threshold.

    Args:
        list_item (ListItem): The list to draw.

    Returns:
        str: Mermaid ``flowchart`` source.

    """
    lines = ["flowchart TD"]
    edges: list[str] = []
    outer_ids: list[str] = []
    for outer in list_item.outerblockitem_set.order_by("position"):
        outer_ids.append(f"O{outer.pk}")
        suffix = " (randomised blocks)" if outer.randomise_inner_blocks else ""
        lines.append(
            f'  subgraph O{outer.pk}["Outer: {_text(outer.outer_block_name)}{suffix}"]'
        )
        block_ids: list[str] = []
        for block in outer.blockitem_set.order_by("position"):
            block_ids.append(f"B{block.pk}")
            suffix = " (randomised)" if block.randomise_trials else ""
            lines.append(
                f'    subgraph B{block.pk}["Block: {_text(block.label)}{suffix}"]'
            )
            trial_ids: list[str] = []
            for trial in block.trialitem_set.order_by("position"):
                if trial.is_attention_getter:
                    lines.append(f'      T{trial.pk}(["{_text(trial.label)}"])')
                    edges.append(f"  class T{trial.pk} ag")
                    continue
                lines.append(f'      T{trial.pk}["{_text(trial.label)}"]')
                trial_ids.append(f"T{trial.pk}")
                if trial.attention_getter_id:
                    edges.append(_dwell_edge(trial))
            if not block.randomise_trials:
                lines.extend("  " + e for e in _chain(trial_ids))
            lines.append("    end")
        lines.append("  end")
        if not outer.randomise_inner_blocks:
            edges.extend(_chain(block_ids))
    if not outer_ids:
        return 'flowchart TD\n  empty["No trials yet"]'
    edges.extend(_chain(outer_ids))
    lines.extend(edges)
    lines.append("  classDef ag stroke-dasharray: 4 3")
    return "\n".join(lines)
