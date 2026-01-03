"""LLM service for OpenRouter API integration."""

import tomllib
from pathlib import Path
from typing import Any

import httpx
import tomli_w

from ..core.config import APP_DIR, ensure_app_dir, get_config_value

PROMPTS_PATH = APP_DIR / "prompts.toml"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

DEFAULT_PROMPTS = {
    "funny": {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "prompt": """You are a video content strategist. Create ONE funny video idea that:
- Can be filmed and edited in under 2 hours total
- Has viral potential with humor
- Includes a catchy title, hook, and brief outline

Here are some of my existing scripts for context on topics and style:
{scripts}

Be specific and actionable. Output the idea as a ready-to-film script outline.""",
    },
    "relevant": {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "prompt": """You are a video content strategist. Create ONE timely, relevant video idea that:
- Can be filmed and edited in under 2 hours total
- Taps into current trends or news
- Includes a catchy title, hook, and brief outline

Here are some of my existing scripts for context on topics and style:
{scripts}

Be specific and actionable. Output the idea as a ready-to-film script outline.""",
    },
    "interesting": {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "prompt": """You are a video content strategist. Create ONE interesting, educational video idea that:
- Can be filmed and edited in under 2 hours total
- Teaches something valuable or reveals surprising facts
- Includes a catchy title, hook, and brief outline

Here are some of my existing scripts for context on topics and style:
{scripts}

Be specific and actionable. Output the idea as a ready-to-film script outline.""",
    },
    "remake": {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "prompt": """You are a video content strategist. Given these 5 existing scripts, create ONE fresh remix that:
- Combines the best elements from multiple scripts
- Can be filmed and edited in under 2 hours total
- Feels fresh while leveraging proven content
- Includes a catchy title, hook, and brief outline

EXISTING SCRIPTS:
{scripts}

Be specific and actionable. Output the remixed idea as a ready-to-film script outline.""",
    },
}


def load_prompts() -> dict[str, Any]:
    """Load prompts from TOML file, creating defaults if missing."""
    ensure_app_dir()

    if not PROMPTS_PATH.exists():
        save_prompts(DEFAULT_PROMPTS)
        return DEFAULT_PROMPTS.copy()

    with open(PROMPTS_PATH, "rb") as f:
        return tomllib.load(f)


def save_prompts(prompts: dict[str, Any]) -> None:
    """Save prompts to TOML file."""
    ensure_app_dir()

    with open(PROMPTS_PATH, "wb") as f:
        tomli_w.dump(prompts, f)


def get_prompt(prompt_type: str) -> dict[str, str] | None:
    """Get prompt config by type (funny, relevant, interesting, remake).

    Returns dict with 'model' and 'prompt' keys, or None if not found.
    """
    prompts = load_prompts()
    return prompts.get(prompt_type)


def generate(prompt: str, model: str) -> dict[str, Any]:
    """Call OpenRouter API to generate content.

    Returns dict with 'content', 'model', and 'tokens_used' keys.
    Raises exception on API error.
    """
    api_key = get_config_value("api.openrouter_key")

    if not api_key:
        raise ValueError(
            "OpenRouter API key not configured. "
            "Set it with: bmc config set api.openrouter_key YOUR_KEY"
        )

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )

        if response.status_code != 200:
            error_msg = response.text
            raise RuntimeError(f"OpenRouter API error ({response.status_code}): {error_msg}")

        data = response.json()

        return {
            "content": data["choices"][0]["message"]["content"],
            "model": data.get("model", model),
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
        }
