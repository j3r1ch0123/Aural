# migrations/v2_indexes.py
def migrate(conn):
    """Add performance indexes"""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_query ON research_results(query)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON research_results(source)")
    conn.commit()
