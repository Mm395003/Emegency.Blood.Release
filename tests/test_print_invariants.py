"""Guardrails for tag/report print dimensions and branding."""

import re
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


def _home_section():
    start = HTML.index('<section id="home"')
    return HTML[start:HTML.index("</section>", start)]


def test_header_crimson_and_identity():
    assert "--crimson:#8E1B2C" in HTML
    assert ".header{" in HTML and "background:var(--crimson)" in HTML
    assert "BLOOD BANK" in HTML
    assert "Laboratory Department" not in HTML


def test_homepage_hero_and_three_cards():
    home = _home_section()
    assert "Emergency Blood Release" in home
    assert "Every Second Matters. Every Unit Counts." in home
    assert home.count('class="action-card') == 3
    assert "openCreateTag()" in home and "show('history')" in home and "show('dashboard')" in home
    assert "show('tagPage')" not in home and "show('issueReport')" not in home
    after_slogan = home.split("Every Second Matters. Every Unit Counts.</p>", 1)[1]
    assert not re.search(r"<p[\s>]", after_slogan)
    assert "<img" not in home


def test_nav_items_and_admin_gate():
    for label in ["Home", "Create Tag", "Requests", "Tag Preview", "Issue Report", "History", "Admin"]:
        assert f"<span>{label}</span>" in HTML
    assert "<span>Audit Trail</span>" not in HTML
    assert 'id="usersNav"' in HTML and 'style="display:none"' in HTML


def test_history_date_range_filter():
    assert 'id="histFrom"' in HTML and 'id="histTo"' in HTML
    assert "function filteredHistory" in HTML
    assert "downloadCSV(filteredHistory()" in HTML


def test_request_number_saved_and_new_tag_resets():
    assert "function allocateRequestNo" in HTML and "/api/request-number" in HTML
    assert "requestNo:x.requestNo||currentRequestNo()" in HTML
    assert "<th>Request No.</th>" in HTML
    assert HTML.count('onclick="newTag()"') >= 3
    new_tag = HTML.split("function newTag(){", 1)[1].split("\nfunction ", 1)[0]
    for step in ["clearForm()", "clearIssueUnits()", "allocateRequestNo()"]:
        assert step in new_tag


def test_technologist_name_remembered_per_user():
    assert "function savedTechName" in HTML and "'techName:'" in HTML
    assert "$('tech').value=savedTechName();" in HTML
    assert "$('tech').value='';" not in HTML


def test_request_list_and_open_request():
    assert '<section id="requests" class="page">' in HTML
    assert '<section id="requestDetail" class="page">' in HTML
    assert "function requestGroups" in HTML and "function openRequest" in HTML
    open_fn = HTML.split("function openRequest(no){", 1)[1].split("\nfunction ", 1)[0]
    assert "setIssueUnits(" in open_fn
    assert "saveHistoryRecord" not in open_fn
    assert "pg:$('pg')?.value" in HTML and "exp:x.exp" in HTML


def test_reopened_request_keeps_original_issue_time():
    report = HTML.split("function issueReportView(){", 1)[1].split("\nfunction ", 1)[0]
    assert "$('ir_time').textContent=now()" not in report
    assert "x.dt" in report
    assert "dt:x.dt||now()" in HTML
