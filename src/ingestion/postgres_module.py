from src.graph.connection import get_postgres_connection
from datetime import datetime

# ── POSTGRESQL MODULE ─────────────────────────────────────────────────────────
# Stores and retrieves:
#   - Market signals (price spikes, lead time changes, news)
#   - Disruption events (what happened, impact, response)
#   - Audit logs (every ASCNS action)
#   - Risk snapshots (drift score history over time)
# ─────────────────────────────────────────────────────────────────────────────

# ── MARKET SIGNALS ────────────────────────────────────────────────────────────

def log_market_signal(signal_type, source, affected_country,
                      affected_industry, severity, description):
    """
    Log a market signal detected by ASCNS.
    Examples: price spike, lead time increase, port closure, news event.
    """
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO market_signals
            (signal_type, source, affected_country,
             affected_industry, severity, description)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (signal_type, source, affected_country,
          affected_industry, severity, description))
    signal_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    print(f"Market signal logged: [{signal_type}] {description[:50]}...")
    return signal_id

def get_recent_signals(limit=10):
    """Get the most recent market signals."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, signal_type, source, affected_country,
               affected_industry, severity, description, detected_at
        FROM market_signals
        ORDER BY detected_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id":                 r[0],
            "signal_type":        r[1],
            "source":             r[2],
            "affected_country":   r[3],
            "affected_industry":  r[4],
            "severity":           r[5],
            "description":        r[6],
            "detected_at":        str(r[7])
        }
        for r in rows
    ]

def get_high_severity_signals(threshold=0.7):
    """Get signals above a severity threshold — these need immediate attention."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT signal_type, affected_country, affected_industry,
               severity, description, detected_at
        FROM market_signals
        WHERE severity >= %s
        ORDER BY severity DESC, detected_at DESC
    """, (threshold,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "signal_type":       r[0],
            "affected_country":  r[1],
            "affected_industry": r[2],
            "severity":          r[3],
            "description":       r[4],
            "detected_at":       str(r[5])
        }
        for r in rows
    ]

# ── DISRUPTION EVENTS ─────────────────────────────────────────────────────────

def log_disruption_event(event_type, severity, affected_suppliers,
                         financial_impact, drift_score, action_taken, outcome):
    """Log a disruption event and ASCNS response."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO disruption_events
            (event_type, severity, affected_suppliers, financial_impact,
             drift_score_at_time, action_taken, outcome)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (event_type, severity,
          ','.join(affected_suppliers) if isinstance(affected_suppliers, list) else affected_suppliers,
          financial_impact, drift_score, action_taken, outcome))
    event_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    print(f"Disruption event logged: [{event_type}] severity={severity}")
    return event_id

def get_disruption_history(limit=10):
    """Get history of disruption events."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT event_type, severity, affected_suppliers,
               financial_impact, drift_score_at_time,
               action_taken, outcome, created_at
        FROM disruption_events
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "event_type":        r[0],
            "severity":          r[1],
            "affected_suppliers": r[2],
            "financial_impact":  r[3],
            "drift_score":       r[4],
            "action_taken":      r[5],
            "outcome":           r[6],
            "created_at":        str(r[7])
        }
        for r in rows
    ]

# ── RISK SNAPSHOTS ────────────────────────────────────────────────────────────

def save_risk_snapshot(drift_score, composite_risk, risk_level,
                       hidden_deps, chokepoints):
    """Save a point-in-time risk snapshot for trend analysis."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO risk_snapshots
            (drift_score, composite_risk, risk_level, hidden_deps, chokepoints)
        VALUES (%s, %s, %s, %s, %s)
    """, (drift_score, composite_risk, risk_level, hidden_deps, chokepoints))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Risk snapshot saved: drift={drift_score}% level={risk_level}")

def get_risk_trend(limit=30):
    """Get risk trend over time — for dashboard chart."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT drift_score, composite_risk, risk_level,
               hidden_deps, chokepoints, snapshot_at
        FROM risk_snapshots
        ORDER BY snapshot_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "drift_score":    r[0],
            "composite_risk": r[1],
            "risk_level":     r[2],
            "hidden_deps":    r[3],
            "chokepoints":    r[4],
            "snapshot_at":    str(r[5])
        }
        for r in rows
    ]

# ── AUDIT LOG ─────────────────────────────────────────────────────────────────

def log_action(action, details, performed_by="ASCNS"):
    """Log any ASCNS action to the audit trail."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO audit_log (action, performed_by, details)
        VALUES (%s, %s, %s)
    """, (action, performed_by, details))
    conn.commit()
    cur.close()
    conn.close()

def get_audit_log(limit=20):
    """Get recent audit log entries."""
    conn = get_postgres_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT action, performed_by, details, created_at
        FROM audit_log
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "action":       r[0],
            "performed_by": r[1],
            "details":      r[2],
            "created_at":   str(r[3])
        }
        for r in rows
    ]

# ── SUPPLIERS FROM POSTGRES ───────────────────────────────────────────────────

def get_suppliers_from_postgres(tier=None, country=None, limit=100):
    """Query suppliers from PostgreSQL with optional filters."""
    conn = get_postgres_connection()
    cur  = conn.cursor()

    query  = "SELECT supplier_id, name, country, tier, industry, product, lead_time_days, annual_value, risk_score FROM suppliers WHERE 1=1"
    params = []

    if tier is not None:
        query += " AND tier = %s"
        params.append(tier)
    if country:
        query += " AND country ILIKE %s"
        params.append(f"%{country}%")

    query += f" ORDER BY tier, annual_value DESC LIMIT {limit}"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "supplier_id":    r[0],
            "name":           r[1],
            "country":        r[2],
            "tier":           r[3],
            "industry":       r[4],
            "product":        r[5],
            "lead_time_days": r[6],
            "annual_value":   r[7],
            "risk_score":     r[8]
        }
        for r in rows
    ]

def seed_sample_signals():
    """Seed some sample market signals for testing."""
    print("\nSeeding sample market signals...")

    signals = [
        ("PRICE_SPIKE",    "Market Feed", "China",  "Semiconductors", 0.85,
         "Silicon prices up 34% in 2 weeks — demand surge detected"),
        ("LEAD_TIME_INC",  "Logistics",   "Taiwan", "Electronics",    0.72,
         "ChipMaker lead times extended from 8 to 14 weeks"),
        ("PORT_CLOSURE",   "News",        "China",  "Manufacturing",  0.65,
         "Shenzhen port partial closure affecting 30% of throughput"),
        ("GEOPOLITICAL",   "Intelligence","China",  "General",        0.90,
         "Trade tensions escalating — tariff increase likely within 30 days"),
        ("FINANCIAL",      "Market Feed", "Congo",  "Raw Materials",  0.55,
         "Currency volatility in DRC affecting rare metal pricing"),
    ]

    for s in signals:
        log_market_signal(*s)

    print(f"Seeded {len(signals)} market signals")

def run_postgres_demo():
    """Run a full PostgreSQL module demo."""
    print("\n" + "="*60)
    print("   ASCNS POSTGRESQL MODULE DEMO")
    print("="*60)

    # Seed signals
    seed_sample_signals()

    # Log a disruption event
    log_disruption_event(
        event_type="geopolitical",
        severity=3,
        affected_suppliers=["AlphaElec", "BetaManuf", "GammaParts"],
        financial_impact=2740500,
        drift_score=48,
        action_taken="Emergency supplier audit initiated, buffer inventory ordered",
        outcome="MITIGATED"
    )

    # Save risk snapshot
    save_risk_snapshot(
        drift_score=48,
        composite_risk=37,
        risk_level="MEDIUM",
        hidden_deps=3,
        chokepoints=2
    )

    # Log action
    log_action(
        "RISK_ASSESSMENT",
        "Automated risk assessment completed. Drift=48%, Composite=37/100"
    )

    # Show results
    print("\n Recent Market Signals:")
    for s in get_recent_signals(3):
        print(f"  [{s['signal_type']}] {s['description'][:60]}...")

    print("\n High Severity Signals (>0.7):")
    for s in get_high_severity_signals(0.7):
        print(f"  {s['signal_type']} | {s['affected_country']} | severity={s['severity']}")

    print("\n Disruption History:")
    for e in get_disruption_history(2):
        print(f"  [{e['event_type']}] impact=${e['financial_impact']:,.0f} | {e['outcome']}")

    print("\n Risk Trend:")
    for r in get_risk_trend(3):
        print(f"  drift={r['drift_score']}% | risk={r['composite_risk']}/100 | {r['risk_level']}")

    print("\n Audit Log:")
    for a in get_audit_log(3):
        print(f"  [{a['action']}] {a['details'][:60]}...")

    print("\n" + "="*60)

if __name__ == "__main__":
    run_postgres_demo()