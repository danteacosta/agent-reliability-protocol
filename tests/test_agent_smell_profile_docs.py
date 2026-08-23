from pathlib import Path


def test_profile_disambiguates_runtime_native_from_hidden_reasoning_and_snapshots():
    text = (Path(__file__).parents[1] / "docs/profiles/agent-smell-degradation-v1.md").read_text(
        encoding="utf-8"
    )
    assert "externally materialized" in text
    assert "chain-of-thought" in text
    assert "retrospective/prompted snapshot" in text
    assert "available to the feature plane before" in text
