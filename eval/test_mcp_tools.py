from __future__ import annotations

from api.mcp import tools as mcp_tools


def test_predict_price_delegates(monkeypatch):
    expected = {
        "predicted_price": 515000,
        "predicted_price_low": 480000,
        "predicted_price_high": 550000,
        "confidence_level": "medium",
    }

    monkeypatch.setattr(mcp_tools, "_predict_house_price", lambda details: expected)

    assert mcp_tools.predict_price({"address": "123 Main St"}) == expected


def test_get_comps_honors_top_n(monkeypatch):
    calls = {}

    def fake_rank(details, top_n=15):
        calls["top_n"] = top_n
        return [{"address": "1 Main St"}, {"address": "2 Main St"}][:top_n]

    monkeypatch.setattr(
        mcp_tools,
        "_rank_and_summarize_comps",
        lambda details, top_n=15: fake_rank(details, top_n=top_n),
    )

    result = mcp_tools.get_comps({"address": "123 Main St"}, top_n=1)

    assert calls["top_n"] == 1
    assert result == [{"address": "1 Main St"}]


def test_explain_price_preserves_payload(monkeypatch):
    expected = {"kind": "price", "top_positive": [], "top_negative": []}

    monkeypatch.setattr(mcp_tools, "_explain_house_price", lambda details, top_n=5: expected)

    assert mcp_tools.explain_price({"address": "123 Main St"}, top_n=3) == expected


def test_explain_comps_preserves_payload(monkeypatch):
    expected = {"kind": "comps", "top_comps": []}

    monkeypatch.setattr(mcp_tools, "_explain_comps", lambda details, top_n=5: expected)

    assert mcp_tools.explain_comps({"address": "123 Main St"}, top_n=2) == expected


def test_export_comps_csv_handles_missing_previous_comps(monkeypatch):
    expected = {"status": "missing_comps", "csv": "", "rows": []}

    monkeypatch.setattr(
        mcp_tools,
        "_build_csv_export_payload",
        lambda message, last_analysis, top_n=None, addresses=None: expected,
    )

    assert mcp_tools.export_comps_csv("export comps", None) == expected


def test_export_comps_csv_success_delegates_selection(monkeypatch):
    expected = {
        "status": "ready",
        "filename": "comps-export-1.csv",
        "csv": "address\n1 Main St\n",
        "rows": [{"address": "1 Main St"}],
    }
    calls = {}

    def fake_export(message, last_analysis, top_n=None, addresses=None):
        calls.update(
            {
                "message": message,
                "last_analysis": last_analysis,
                "top_n": top_n,
                "addresses": addresses,
            }
        )
        return expected

    monkeypatch.setattr(mcp_tools, "_build_csv_export_payload", fake_export)

    last_analysis = {"comps_table": [{"address": "1 Main St"}]}
    result = mcp_tools.export_comps_csv(
        "export top 1",
        last_analysis,
        top_n=1,
        addresses=["1 Main St"],
    )

    assert result == expected
    assert calls == {
        "message": "export top 1",
        "last_analysis": last_analysis,
        "top_n": 1,
        "addresses": ["1 Main St"],
    }


def test_parse_house_pdf_delegates(monkeypatch):
    expected = {"details": {"address": "123 Main St"}, "summary": "parsed"}

    monkeypatch.setattr(
        mcp_tools,
        "_parse_house_details_pdf",
        lambda data_base64, mime_type="application/pdf": expected,
    )

    assert mcp_tools.parse_house_pdf("abc", "application/pdf") == expected


def test_run_chat_turn_preserves_response_shape(monkeypatch):
    expected = {"answer": "ok", "conversation_id": "chat-1", "comps": []}

    monkeypatch.setattr(
        mcp_tools,
        "_build_response",
        lambda message, house_details, conversation_id, conversation_history=None: expected,
    )

    assert mcp_tools.run_chat_turn(
        "hello",
        {"address": "123 Main St"},
        "chat-1",
        [{"role": "user", "content": "hello"}],
    ) == expected
