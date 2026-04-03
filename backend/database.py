import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'karedefteri.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user' CHECK(role IN ('user', 'admin')),
        is_active INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        ban_reason TEXT,
        banned_at TEXT,
        country TEXT DEFAULT '',
        profile_pic TEXT DEFAULT '',
        bio TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );

    -- Email verification codes
    CREATE TABLE IF NOT EXISTS verification_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Posts (images only)
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        image_path TEXT NOT NULL,
        caption TEXT DEFAULT '',
        is_visible INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Follows (directed relationship)
    CREATE TABLE IF NOT EXISTS follows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER NOT NULL,
        following_id INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(follower_id, following_id)
    );

    -- Likes / Dislikes
    CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        reaction_type TEXT NOT NULL CHECK(reaction_type IN ('like', 'dislike')),
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        UNIQUE(user_id, post_id)
    );

    -- Reports
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        reason TEXT DEFAULT '',
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'reviewed', 'dismissed')),
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        UNIQUE(reporter_id, post_id)
    );

    -- Stories (extra feature)
    CREATE TABLE IF NOT EXISTS stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        image_path TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Story views
    CREATE TABLE IF NOT EXISTS story_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        story_id INTEGER NOT NULL,
        viewer_id INTEGER NOT NULL,
        viewed_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
        FOREIGN KEY (viewer_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(story_id, viewer_id)
    );

    -- Ban logs
    CREATE TABLE IF NOT EXISTS ban_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('ban', 'unban')),
        reason TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (admin_id) REFERENCES users(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
    CREATE INDEX IF NOT EXISTS idx_posts_visible ON posts(is_visible);
    CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_id);
    CREATE INDEX IF NOT EXISTS idx_follows_following ON follows(following_id);
    CREATE INDEX IF NOT EXISTS idx_reactions_post ON reactions(post_id);
    CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
    CREATE INDEX IF NOT EXISTS idx_stories_user ON stories(user_id);
    CREATE INDEX IF NOT EXISTS idx_stories_expires ON stories(expires_at);
    ''')

    # Create default admin if not exists
    import bcrypt
    admin_check = cursor.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin_check:
        pw_hash = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, is_active, country)
            VALUES ('admin', 'admin@karedefteri.com', ?, 'admin', 1, 'TR')
        """, (pw_hash,))

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
