import sqlite3
import json
import argparse
import textwrap


def pprint_row(r):
    agent_name, input_text, output_text, output_json, duration, created_at = r
    print(f"AGENT: {agent_name}  (at {created_at}, {duration}s)")
    print("INPUT:\n")
    print(textwrap.indent(input_text or "", "  "))
    print("\nOUTPUT (raw):\n")
    print(textwrap.indent(output_text or "", "  "))
    if output_json:
        try:
            parsed = json.loads(output_json)
            print("\nOUTPUT (parsed JSON):\n")
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception:
            pass
    print("\n" + ("-" * 80) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="coach.db", help="Path to SQLite DB file")
    p.add_argument("--run", type=int, help="Run ID to filter by")
    p.add_argument("--limit", type=int, default=0, help="Limit number of calls (0=all)")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    if args.run:
        q = "select agent_name, input_text, output_text, output_json, duration_seconds, created_at from agent_calls where run_id=? order by id"
        rows = cur.execute(q, (args.run,)).fetchall()
    else:
        q = "select agent_name, input_text, output_text, output_json, duration_seconds, created_at from agent_calls order by id desc"
        rows = cur.execute(q).fetchmany(args.limit or 1000)

    if not rows:
        print("No agent calls found (check run id or DB path).")
        return

    for r in rows:
        pprint_row(r)


if __name__ == "__main__":
    main()
