"""Tests for narrative summarization."""

import pytest

from contributions.narrative import _build_prompt, generate_narrative


@pytest.mark.asyncio
async def test_generate_narrative_returns_none_without_api_key(sample_summary):
    result = await generate_narrative(sample_summary, api_key=None)
    assert result is None


def test_build_prompt_includes_profile(sample_summary):
    prompt = _build_prompt(sample_summary)
    assert "testuser" in prompt
    assert "Test User" in prompt


def test_build_prompt_includes_stats(sample_summary):
    prompt = _build_prompt(sample_summary)
    assert "commits" in prompt
    assert "PRs" in prompt


def test_build_prompt_includes_repos(sample_summary):
    prompt = _build_prompt(sample_summary)
    assert "testuser/myrepo" in prompt
