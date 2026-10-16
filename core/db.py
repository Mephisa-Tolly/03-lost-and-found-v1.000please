import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT NOT NULL,
        time TEXT NOT NULL,
        color TEXT,
        brand TEXT,
        description TEXT NOT NULL,
        images TEXT,
        contact TEXT,
        anonymous INTEGER DEFAULT 0,
        sensitive_level INTEGER DEFAULT 0,
        private_features TEXT,
        status TEXT DEFAULT '待匹配',
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        applicant TEXT,
        answers TEXT,
        status TEXT DEFAULT '待核验',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        type TEXT,
        content TEXT,
        read_flag INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def add_item(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO items (type, title, category, location, time, color, brand,
                       description, images, contact, anonymous, sensitive_level,
                       private_features, status, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("type"), data.get("title"), data.get("category"),
        data.get("location"), data.get("time"), data.get("color"),
        data.get("brand"), data.get("description"), data.get("images"),
        data.get("contact"), data.get("anonymous", 0),
        data.get("sensitive_level", 0), data.get("private_features"),
        data.get("status", "待匹配"), data.get("created_by")
    ))
    conn.commit()
    conn.close()


def list_items(item_type=None, keyword=None):
    conn = get_conn()
    cur = conn.cursor()
    sql = "SELECT * FROM items WHERE 1=1"
    params = []
    if item_type:
        sql += " AND type = ?"
        params.append(item_type)
    if keyword:
        sql += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])
    sql += " ORDER BY created_at DESC"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_item_status(item_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE items SET status = ? WHERE item_id = ?", (status, item_id))
    conn.commit()
    conn.close()


def add_claim(item_id, applicant, answers):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO claims (item_id, applicant, answers)
    VALUES (?, ?, ?)
    """, (item_id, applicant, answers))
    conn.commit()
    conn.close()


def list_claims(item_id=None):
    conn = get_conn()
    cur = conn.cursor()
    if item_id:
        cur.execute("SELECT * FROM claims WHERE item_id = ? ORDER BY created_at DESC", (item_id,))
    else:
        cur.execute("SELECT * FROM claims ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_claim(claim_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_claim_status(claim_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE claims SET status = ? WHERE claim_id = ?", (status, claim_id))
    conn.commit()
    conn.close()


def add_notification(user_id, ntype, content):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO notifications (user_id, type, content)
    VALUES (?, ?, ?)
    """, (user_id, ntype, content))
    conn.commit()
    conn.close()


def list_notifications(user_id=None):
    conn = get_conn()
    cur = conn.cursor()
    if user_id:
        cur.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    else:
        cur.execute("SELECT * FROM notifications ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def mark_notification_read(notification_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET read_flag = 1 WHERE notification_id = ?", (notification_id,))
    conn.commit()
    conn.close()