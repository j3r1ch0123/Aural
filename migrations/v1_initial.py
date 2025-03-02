def migrate(conn):
    """Initial database schema"""
    query = """
    CREATE TABLE IF NOT EXISTS research_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        content TEXT,
        source TEXT,
        published_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    conn.execute(query)
    conn.commit()
