from src.graph.connection import Neo4jConnection
from datetime import datetime
import json

# ── DRIFT ENGINE ──────────────────────────────────────────────────────────────
# Measures how much the ACTUAL supply chain has drifted
# away from the DECLARED supply chain map.
#
# Drift Score = 0%  → Declared map perfectly matches reality
# Drift Score = 100% → Declared map is completely wrong
# ─────────────────────────────────────────────────────────────────────────────

def get_declared_link_count():
    """Count all declared (ERP) relationships."""
    query = "MATCH ()-[r:DECLARED_SUPPLIES]->() RETURN count(r) as total"
    result = Neo4jConnection.run_query(query)
    return result[0]['total'] if result else 0

def get_inferred_link_count():
    """Count all inferred (ASCNS detected) relationships."""
    query = "MATCH ()-[r:INFERRED_SUPPLIES]->() RETURN count(r) as total"
    result = Neo4jConnection.run_query(query)
    return result[0]['total'] if result else 0

def get_undeclared_dependencies():
    """
    Find suppliers that are inferred but NOT declared.
    These are the hidden relationships — the core of drift.
    """
    query = """
    MATCH (a:Supplier)-[r:INFERRED_SUPPLIES]->(b:Supplier)
    WHERE NOT (a)-[:DECLARED_SUPPLIES]->(b)
    RETURN a.name as from_supplier,
           b.name as to_supplier,
           b.country as country,
           b.tier as tier,
           r.probability as probability,
           r.product as product
    ORDER BY r.probability DESC
    """
    return Neo4jConnection.run_query(query)

def get_high_probability_hidden_links():
    """
    Inferred links with probability > 0.80 —
    these are almost certainly real but undeclared.
    High drift indicators.
    """
    query = """
    MATCH (a:Supplier)-[r:INFERRED_SUPPLIES]->(b:Supplier)
    WHERE r.probability > 0.80
    AND NOT (a)-[:DECLARED_SUPPLIES]->(b)
    RETURN a.name as from_supplier,
           b.name as to_supplier,
           r.probability as probability,
           r.product as product,
           b.country as country
    ORDER BY r.probability DESC
    """
    return Neo4jConnection.run_query(query)

def get_tier_drift_breakdown():
    """
    Calculate drift score per tier —
    which tier is drifting the most from declared?
    """
    query = """
    MATCH (a:Supplier)-[r:INFERRED_SUPPLIES]->(b:Supplier)
    WHERE NOT (a)-[:DECLARED_SUPPLIES]->(b)
    RETURN b.tier as tier,
           count(r) as hidden_links,
           avg(r.probability) as avg_probability
    ORDER BY tier
    """
    return Neo4jConnection.run_query(query)

def calculate_drift_score():
    """
    Core Drift Score calculation.

    Formula:
      Base drift = hidden links / total links
      Weighted by average probability of hidden links
      Amplified by tier depth (deeper = more dangerous)

    Returns a score from 0 to 100.
    """
    declared = get_declared_link_count()
    inferred = get_inferred_link_count()
    hidden = get_undeclared_dependencies()
    high_prob = get_high_probability_hidden_links()

    if declared == 0:
        return {
            "drift_score": 0,
            "level": "UNKNOWN",
            "reason": "No declared links found"
        }

    total_links = declared + inferred
    hidden_count = len(hidden)

    # Base drift ratio
    base_drift = (hidden_count / total_links) * 100 if total_links > 0 else 0

    # Weight by average probability
    if hidden:
        avg_prob = sum(h['probability'] for h in hidden) / len(hidden)
    else:
        avg_prob = 0

    # High probability hidden links are more dangerous
    high_prob_penalty = len(high_prob) * 8

    # Final drift score (capped at 100)
    drift_score = min(100, round(base_drift * avg_prob + high_prob_penalty))

    # Drift level
    if drift_score >= 70:
        level = "CRITICAL"
        color = "#ff4444"
        action = "Immediate supplier audit required"
    elif drift_score >= 45:
        level = "HIGH"
        color = "#ff6b6b"
        action = "Review inferred dependencies within 48 hours"
    elif drift_score >= 20:
        level = "MEDIUM"
        color = "#f39c12"
        action = "Monitor closely — schedule supplier review"
    else:
        level = "LOW"
        color = "#1D9E75"
        action = "Supply chain map is reasonably accurate"

    return {
        "drift_score": drift_score,
        "level": level,
        "color": color,
        "action": action,
        "declared_links": declared,
        "inferred_links": inferred,
        "hidden_links": hidden_count,
        "high_probability_hidden": len(high_prob),
        "calculated_at": datetime.utcnow().isoformat()
    }

def get_full_drift_report():
    """
    Full drift report — everything ASCNS knows
    about the gap between declared and actual network.
    """
    print("\n" + "="*60)
    print("   ASCNS TOPOLOGY DRIFT REPORT")
    print("="*60)

    # Drift score
    score = calculate_drift_score()
    print(f"\n DRIFT SCORE: {score['drift_score']}% — {score['level']}")
    print(f" Action: {score['action']}")
    print(f"\n Declared links:          {score['declared_links']}")
    print(f" Inferred links:          {score['inferred_links']}")
    print(f" Hidden (undeclared):     {score['hidden_links']}")
    print(f" High-probability hidden: {score['high_probability_hidden']}")

    # Hidden dependencies detail
    hidden = get_undeclared_dependencies()
    if hidden:
        print(f"\n HIDDEN DEPENDENCIES DETECTED ({len(hidden)}):")
        print("-"*60)
        for h in hidden:
            prob_bar = "█" * int(h['probability'] * 10)
            print(f"  {h['from_supplier']} → {h['to_supplier']}")
            print(f"  Country: {h['country']} | Tier: {h['tier']}")
            print(f"  Product: {h['product']}")
            print(f"  Probability: {prob_bar} {h['probability']:.0%}")
            print()

    # Tier breakdown
    tier_drift = get_tier_drift_breakdown()
    if tier_drift:
        print(" DRIFT BY TIER:")
        print("-"*60)
        for t in tier_drift:
            print(f"  Tier {t['tier']}: {t['hidden_links']} hidden links "
                  f"(avg probability: {t['avg_probability']:.0%})")

    print("\n" + "="*60)
    return score

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    report = get_full_drift_report()