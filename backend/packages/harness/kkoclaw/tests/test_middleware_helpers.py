"""Ported middleware helper modules import and behave."""
from kkoclaw.agents.middlewares._bounded_dict import BoundedDict
from kkoclaw.agents.middlewares.delegation_ledger import (
    extract_delegations,
    render_delegation_ledger,
)


def test_bounded_dict_evicts_oldest():
    d = BoundedDict(maxsize=2)
    d["a"] = 1
    d["b"] = 2
    d["c"] = 3  # exceeds maxsize=2 -> evicts "a"
    assert "a" not in d
    assert d["b"] == 2
    assert d["c"] == 3


def test_render_delegation_ledger_empty():
    # render of an empty ledger is a safe (possibly empty) string
    out = render_delegation_ledger([])
    assert isinstance(out, str)


def test_extract_delegations_empty():
    assert extract_delegations([]) == []
