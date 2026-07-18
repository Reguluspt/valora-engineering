"""S13-PR-002 thirteenth suite — N-01 canonical tests retained.

N-02/N-03/N-04 evidence authority moved to the fourteenth static ledger gate.
This module keeps Enum/type collision regressions without circular-manifest APIs.
"""
from __future__ import annotations

from enum import Enum, IntEnum
from pathlib import Path

import pytest

import app.modules.excel_import.models  # noqa: F401
from app.modules.project_master_data.models import (
    AssetLineReviewStatus,
    ImportBatchStatus,
)
from tests.support.s13_pr_002_http_preserve import (
    assert_canonical_distinguishes_collisions,
    assert_pytest_collect_count_exactly,
    canonical,
    parse_pytest_collect_selected_count,
)
from tests.support.s13_pr_002_matrix import (
    EXPECTED_HTTP_NPLUS1_COUNT,
    validate_collection_matches_ledger,
    ledger_rows,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_n01_canonical_enum_before_scalar_bases():
    assert_canonical_distinguishes_collisions()


def test_n01_project_string_enums_vs_scalars():
    assert canonical(ImportBatchStatus.CREATED) != canonical("created")
    assert canonical(AssetLineReviewStatus.PENDING) != canonical("pending")
    a = canonical(ImportBatchStatus.CREATED)
    assert a[0] == "enum"
    assert a[2] == "ImportBatchStatus"


def test_n01_intenum_vs_int():
    class LocalInt(IntEnum):
        ONE = 1

    assert canonical(LocalInt.ONE) != canonical(1)


def test_n01_two_enum_classes_same_value():
    class OtherCreated(str, Enum):
        CREATED = "created"

    assert canonical(ImportBatchStatus.CREATED) != canonical(OtherCreated.CREATED)


def test_n01_typed_dict_keys_and_stable_order():
    import uuid

    u = uuid.UUID(int=9)
    assert canonical({1: "x"}) != canonical({"1": "x"})
    assert canonical({u: "x"}) != canonical({str(u): "x"})
    assert canonical({"z": 1, "a": 2}) == canonical({"a": 2, "z": 1})


def test_n01_unsupported_type_fail_closed():
    with pytest.raises(TypeError):
        canonical(object())


def test_n04_parse_collect_count_exact_and_rejects_148():
    assert parse_pytest_collect_selected_count("48/831 tests collected in 0.4s\n") == 48
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly(
            "148/831 tests collected in 0.4s\n", expected=48, returncode=0
        )
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly(
            "no summary here\n", expected=48, returncode=0
        )


def test_n04_live_collect_matches_static_ledger():
    import subprocess
    import sys

    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-m",
            "s13_pr_002_http_nplus1_reject",
            "-q",
        ],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    out = (r.stdout or "") + (r.stderr or "")
    assert_pytest_collect_count_exactly(
        out, expected=EXPECTED_HTTP_NPLUS1_COUNT, returncode=r.returncode
    )
    nodes = [
        line.strip()
        for line in (r.stdout or "").splitlines()
        if "::" in line and "test_" in line
    ]
    validate_collection_matches_ledger(nodes, ledger_rows())
