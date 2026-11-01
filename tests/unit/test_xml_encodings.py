"""A re-encoded document must not slip an entity declaration past the guard."""

from __future__ import annotations

import pytest

from proofboard.checks import coverage_percent, junit_totals

BOMB = (
    '<?xml version="1.0"?><!DOCTYPE testsuite [<!ENTITY a "AAAAAAAAAA">]>'
    '<testsuite tests="1" failures="0" errors="0" name="&a;"><testcase name="x"/></testsuite>'
)
CLEAN = '<testsuite tests="1" failures="0" errors="0"><testcase name="x"/></testsuite>'


@pytest.mark.parametrize(
    "encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "utf-32"]
)
def test_entities_are_refused_in_every_encoding(encoding: str) -> None:
    assert junit_totals(BOMB.encode(encoding)) is None


def test_ebcdic_declared_encoding_is_refused() -> None:
    declared = BOMB.replace('<?xml version="1.0"?>', '<?xml version="1.0" encoding="cp037"?>')
    assert junit_totals(declared.encode("cp037")) is None


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le"])
def test_clean_documents_in_other_encodings_still_parse(encoding: str) -> None:
    assert junit_totals(CLEAN.encode(encoding)) == (1, 0, 0)


def test_plain_and_bom_utf8_still_work() -> None:
    assert junit_totals(CLEAN.encode("utf-8")) == (1, 0, 0)
    assert junit_totals(CLEAN.encode("utf-8-sig")) == (1, 0, 0)
    declared = '<?xml version="1.0" encoding="UTF-8"?>' + CLEAN
    assert junit_totals(declared.encode("utf-8")) == (1, 0, 0)


def test_a_nul_byte_is_refused() -> None:
    assert junit_totals(CLEAN.replace("x", "x\x00").encode("utf-8")) is None


def test_coverage_xml_goes_through_the_same_guard() -> None:
    xml = '<coverage line-rate="0.93"></coverage>'
    assert coverage_percent("coverage.xml", xml.encode("utf-8"), xml) == 93.0
    assert coverage_percent("coverage.xml", xml.encode("utf-16"), xml) == 93.0
