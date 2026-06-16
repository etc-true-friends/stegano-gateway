import sqlite3


DB_PATH = r"D:\DevelopSource\goorm\stegano-gateway\2_API_Gateway\test.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("DB_PATH:", DB_PATH)
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print("TABLES:", tables)

    for t in tables:
        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
        # (cid, name, type, notnull, dflt_value, pk)
        print(f"\n-- {t} --")
        for c in cols:
            print(" ", {"name": c[1], "type": c[2], "pk": bool(c[5])})

    # quick row counts (useful for debugging endpoints)
    print("\nROW_COUNTS:")
    for t in tables:
        try:
            cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            cnt = None
        print(" ", t, "=>", cnt)

    # show a few mail rows
    try:
        print("\nMAIL_SAMPLE:")
        for r in cur.execute(
            "SELECT id, sender_id, mailbox_id, parent_mail_id, subject, status, sent_at, created_at FROM mail ORDER BY id DESC LIMIT 3"
        ).fetchall():
            print(" ", dict(zip([d[0] for d in cur.description], r)))
    except Exception:
        pass

    try:
        print("\nMAILBOX_SAMPLE:")
        for r in cur.execute("SELECT id, employee_id, type, created_at FROM mailbox ORDER BY id").fetchall():
            print(" ", dict(zip([d[0] for d in cur.description], r)))
    except Exception:
        pass

    try:
        print("\nMAIL_JOIN_SAMPLE:")
        q = """
        SELECT
          m.id,
          e.username AS sender_username,
          mb.type AS mailbox_type,
          m.subject,
          m.status,
          m.sent_at
        FROM mail m
        JOIN employee e ON e.id = m.sender_id
        JOIN mailbox mb ON mb.id = m.mailbox_id
        WHERE m.b_deleted = 'N'
        ORDER BY m.id DESC
        LIMIT 5
        """
        for r in cur.execute(q).fetchall():
            print(" ", dict(zip([d[0] for d in cur.description], r)))
    except Exception:
        pass

    conn.close()


if __name__ == "__main__":
    main()

