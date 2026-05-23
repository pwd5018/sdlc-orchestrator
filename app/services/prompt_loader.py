from pathlib import Path


def load_prompt(prompt_name: str) -> str:
    project_root = Path(__file__).resolve().parents[2]
    prompt_path = project_root / "prompts" / prompt_name
    return prompt_path.read_text(encoding="utf-8")
