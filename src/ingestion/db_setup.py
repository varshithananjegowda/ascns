from src.graph.connection import get_postgres_connection

def create_tables():
    """Create all PostgreSQL tables for ASCNS."""
    conn = get_postgres_connection()
    cur  = conn.cursor()

    # Suppliers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id              SERIAL PRIMARY KEY,
            supplier_id     VARCHAR(50) UNIQUE NOT NULL,
            name            VARCHAR(200) NOT NULL,
            country         VARCHAR(100),
            tier            INTEGER,
            industry        VARCHAR(100),
            product         VARCHAR(200),
            lead_time_days  INTEGER,
            annual_value    FLOAT,
            risk_score      FLOAT DEFAULT 0.0,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)

    # Market signals table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_signals (
            id              SERIAL PRIMARY KEY,
            signal_type     VARCHAR(100),
            source          VARCHAR(200),
            affected_country VARCHAR(100),
            affected_industry VARCHAR(100),
            severity        FLOAT,
            description     TEXT,
            detected_at     TIMESTAMP DEFAULT NOW()
        )
    """)

    # Disruption events table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS disruption_events (
            id              SERIAL PRIMARY KEY,
            event_type      VARCHAR(100),
            severity        INTEGER,
            affected_suppliers TEXT,
            financial_impact FLOAT,
            drift_score_at_time FLOAT,
            action_taken    TEXT,
            outcome         VARCHAR(100),
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)

    # Audit log table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id              SERIAL PRIMARY KEY,
            action          VARCHAR(200),
            performed_by    VARCHAR(100) DEFAULT 'ASCNS',
            details         TEXT,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)

    # Risk snapshots table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS risk_snapshots (
            id              SERIAL PRIMARY KEY,
            drift_score     FLOAT,
            composite_risk  FLOAT,
            risk_level      VARCHAR(50),
            hidden_deps     INTEGER,
            chokepoints     INTEGER,
            snapshot_at     TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("All PostgreSQL tables created successfully!")

if __name__ == "__main__":
    create_tables()