"""Export the Pydantic event contract as JSON Schema for TypeScript generation."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import TypeAdapter

from src.events import AgentEvent

OUT = ROOT / "docs" / "src" / "types" / "agent-event.schema.json"


def main() -> None:
    schema = TypeAdapter(AgentEvent).json_schema()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
