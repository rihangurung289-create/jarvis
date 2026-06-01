"""Print recent Guardian activity and security incidents."""

import config
from audit import AuditStore


def main() -> None:
    store = AuditStore(config.GUARDIAN_DATA_DIR)
    users = store.list_users()

    print("=" * 60)
    print("Jarvis Guardian — Security Report")
    print("=" * 60)

    print("\nEnrolled users:")
    if not users:
        print("  (none — say 'jarvis enroll user YourName' to register)")
    for user in users:
        print(
            f"  - {user.display_name} (id={user.user_id}, "
            f"samples={user.sample_count}, since={user.enrolled_at[:10]})"
        )

    print("\nRecent activity:")
    activity = store.read_recent_activity(20)
    if not activity:
        print("  (no activity logged yet)")
    for row in activity:
        flags = f" incidents={row['incidents']}" if row.get("incidents") else ""
        print(
            f"  [{row['timestamp'][:19]}] {row['display_name']} "
            f"({row['command_type']}) {row['raw_text']!r}{flags}"
        )

    print("\nRecent incidents (weird behavior):")
    incidents = store.read_recent_incidents(20)
    if not incidents:
        print("  (none)")
    for row in incidents:
        blocked = "BLOCKED" if row.get("blocked") else "flagged"
        print(
            f"  [{row['timestamp'][:19]}] {blocked} {row['display_name']}: "
            f"{', '.join(row['reasons'])} — {row['raw_text']!r}"
        )

    print("\nData folder:", config.GUARDIAN_DATA_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
