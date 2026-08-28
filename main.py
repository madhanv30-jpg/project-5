import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import run_agent, init


def main():
    print("=" * 64)
    print("  MADHAN'S PERSONAL SUPPORT AGENT  (Week 6)")
    print("=" * 64)
    print("\nInitializing knowledge base (Pinecone + BM25)...")
    count = init()
    print(f"Loaded {count} document chunks.\n")

    session_id = str(uuid.uuid4())[:8]
    print(f"Session: {session_id}")
    print("Commands: /remind <msg> | /history | /reminders | quit\n")

    while True:
        try:
            user_input = input("madhan> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye, Madhan.")
            break

        if user_input.lower() == "/history":
            from src.logger import read_session_log
            for entry in read_session_log(session_id):
                print(f"  [{entry.get('kind', entry['role'])}] {entry['content'][:200]}")
            continue

        if user_input.lower() == "/reminders":
            from src.reminders import get_pending_reminders
            for r in get_pending_reminders():
                print(f"  #{r['id']}: {r['message']}")
            continue

        if user_input.startswith("/remind "):
            from src.reminders import add_reminder
            r = add_reminder(user_input[8:])
            print(f"Reminder set: #{r['id']} - {r['message']}")
            continue

        out = run_agent(session_id=session_id, user_input=user_input)
        print(f"\n{out['answer']}\n")
        if out.get("sources"):
            print("  sources:", ", ".join(out["sources"]))
        if out.get("escalated"):
            print("[!] Escalated to Madhan.")
        if out.get("needs_human"):
            print("[!] Flagged for Madhan's attention.")


if __name__ == "__main__":
    main()
