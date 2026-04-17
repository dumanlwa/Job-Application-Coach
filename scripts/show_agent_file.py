import argparse
import json
import textwrap
from pathlib import Path


def wrap(text: str, width: int = 80) -> str:
    return "\n".join(textwrap.fill(line, width=width) for line in text.splitlines())


def indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def show(path: Path, width: int = 80):
    data = json.loads(path.read_text(encoding="utf-8"))

    run_id = data.get("run_id") or data.get("runId") or "-"
    agent = data.get("agent_name") or data.get("agent") or "-"
    created = data.get("created_at") or data.get("createdAt") or "-"

    print(f"Run: {run_id}")
    print(f"Agent: {agent}")
    print(f"Created: {created}")
    print("\n=== INPUT ===\n")
    inp = data.get("input_text") or data.get("input") or ""
    if inp:
        print(indent(wrap(inp, width=width)))
    else:
        print("(no input found)")

    print("\n=== OUTPUT (raw) ===\n")
    out = data.get("output_text") or data.get("output") or ""
    if out:
        print(indent(wrap(out, width=width)))
    else:
        print("(no output found)")

    # If there is parsed JSON output, print it prettily
    parsed = data.get("output_json") or data.get("outputJson")
    if parsed:
        print("\n=== OUTPUT (parsed) ===\n")
        try:
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception:
            print(str(parsed))


def main():
    p = argparse.ArgumentParser(description="Pretty-print an agent JSON file")
    p.add_argument("file", type=Path, help="Path to agent JSON file")
    p.add_argument("--width", type=int, default=80, help="Wrap width")
    args = p.parse_args()

    if not args.file.exists():
        print(f"File not found: {args.file}")
        return

    show(args.file, width=args.width)


if __name__ == "__main__":
    main()

# .\.venv\Scripts\python.exe scripts\show_agent_file.py agent_20260328T083331974152_cover_letter_001.json