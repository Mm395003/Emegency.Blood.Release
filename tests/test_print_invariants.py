"""Guardrails for tag/report print dimensions and branding."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def test_brand_name_without_protocol():
    assert "Emergency Blood Release" in HTML
    assert "Emergency Blood Release Protocol" not in HTML


def test_tag_dimensions_preserved():
    assert "2.71in" in HTML
    assert "5.13in" in HTML
    assert "width:2.71in;height:5.13in" in HTML.replace(" ", "")


def test_a4_issue_report_preserved():
    assert "A4" in HTML
    assert "issue-report" in HTML
    assert "Emergency Release Declaration" in HTML


def test_print_pathways_independent():
    assert "printTagDirect" in HTML or "printAllTagsDirect" in HTML
    assert "printIssueReport" in HTML
    assert "print/tag-bitmap" in HTML


def test_release_workflow_steps_present():
    assert 'data-step-panel="1"' in HTML
    assert 'data-step-panel="2"' in HTML
    assert 'data-step-panel="3"' in HTML
    assert 'data-step-panel="4"' in HTML
    assert "goReleaseStep" in HTML
