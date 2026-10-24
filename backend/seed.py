"""Explicitly synthetic, executable fixture. Code execution is limited to these bytes."""

FILES = {
    "README.md": """# Meadow Notes\n\nA fictional, local-only note tagging library for the PatchGardener demo.\n\nRead the [getting started guide](docs/quickstart.md).\nSee the [API reference](docs/api.md).\n\nRun the example:\n```sh\npython examples/old_demo.py\n```\n\nSynthetic fixture: intentionally planted maintenance issues.\n""",
    "meadow.py": """import os\nimport json\n\n\ndef normalize_tag(value: str) -> str:\n    return value.strip().lower().replace(' ', '-')\n\n\ndef unique_tags(values: list[str]) -> list[str]:\n    return sorted(set(normalize_tag(value) for value in values if value.strip()))\n""",
    "tests/test_meadow.py": """import unittest\nfrom meadow import normalize_tag, unique_tags\n\n\nclass MeadowTests(unittest.TestCase):\n    def test_normalize(self):\n        self.assertEqual(normalize_tag(' Hello World '), 'hello-world')\n\n    def test_unique(self):\n        self.assertEqual(unique_tags(['Green', 'green', 'Blue']), ['blue', 'green'])\n\n    def test_blank(self):\n        self.assertEqual(unique_tags(['', '  ']), [])\n\n\nif __name__ == '__main__':\n    unittest.main()\n""",
    "docs/getting-started.md": "# Getting started\n\nUse `normalize_tag` to turn a label into a tag.\n",
    "docs/api.md": "# API\n\n`normalize_tag(value)` and `unique_tags(values)`.\n",
    "examples/demo.py": "from meadow import unique_tags\n\nprint(unique_tags(['Hello World', 'hello world']))\n",
    "frontend/tags.ts": "export function formatTag(tag: string): string {\nreturn tag.trim().toLowerCase();\n}\n",
    "pyproject.toml": '[project]\nname = "meadow-notes-synthetic"\nversion = "0.0.0"\n\n[tool.ruff]\nline-length = 88\n',
    "auth/session.py": 'import hashlib\n\n\ndef session_label():\n    return "synthetic-protected-path"\n',
}

GROUND_TRUTH = [
    {"path": "meadow.py", "code": "F401", "line": 1},
    {"path": "meadow.py", "code": "F401", "line": 2},
    {"path": "README.md", "code": "MD001", "line": 5},
    {"path": "README.md", "code": "CMD001", "line": 10},
    {"path": "auth/session.py", "code": "F401", "line": 1},
]

# Intentionally outside P0 scanner scope: TS formatting, config redundancy,
# and a missing edge-case test. Do not count these as detected or repaired.
