from src.graph.connection import Neo4jConnection
from src.inference.drift_engine import calculate_drift_score, get_undeclared_dependencies
from datetime import datetime
import random

# ── BEHAVIORAL AMPLIFICATION MODEL ───────────────────────────────────────────
# Models how companies REACT to supply disruptions.
#
# When a disruption signal appears:
#   1. Companies panic-order (demand spikes 2-5x)
#   2. Inventory gets hoarded
#   3. Everyone switches suppliers simultaneously
#   4. This causes MORE damage than the original disruption
#
# ASCNS predicts this cascade BEFORE it happens.
# ─────────────────────────────────────────────────────────────────────────────

# Behavioral parameters
PANIC_THRESHOLD       = 0.35   # Drift score % that triggers panic
HOARD_MULTIPLIER      = 2.8    # How much inventory companies hoard
SIMULTANEOUS_SWITCH   = 0.72   # % of companies that switch supplier at same time
RECOVERY_WEEKS        = 14     # Average weeks to recover from panic cascade

def get_all_suppliers():
    query = "MATCH (s:Supplier) RETURN s ORDER BY s.tier"
    return Neo4jConnection.run_query(query)

def classify_disruption(event_type, severity):
    """
    Map a real-world disruption event to a severity score.
    severity: 1 (minor) to 5 (catastrophic)
    """
    disruption_types = {
        "geopolitical":  {"base_impact": 0.7,  "speed": "fast",   "duration_weeks": 12},
        "climate":       {"base_impact": 0.5,  "speed": "medium", "duration_weeks": 8 },
        "financial":     {"base_impact": 0.4,  "speed": "slow",   "duration_weeks": 16},
        "pandemic":      {"base_impact": 0.9,  "speed": "fast",   "duration_weeks": 26},
        "cyber":         {"base_impact": 0.6,  "speed": "fast",   "duration_weeks": 4 },
        "logistics":     {"base_impact": 0.3,  "speed": "medium", "duration_weeks": 6 },
    }
    d = disruption_types.get(event_type, {"base_impact": 0.5, "speed": "medium", "duration_weeks": 8})
    impact = min(1.0, d["base_impact"] * (severity / 3))
    return {
        "event_type":      event_type,
        "severity":        severity,
        "impact_score":    round(impact, 2),
        "speed":           d["speed"],
        "duration_weeks":  d["duration_weeks"]
    }

def simulate_panic_ordering(disruption, drift_score):
    """
    Simulate how companies panic-order when they see a disruption.

    Key insight: The HIGHER the drift score,
    the more companies panic because they realize
    their supply chain map is wrong.
    """
    base_panic = disruption["impact_score"]

    # Drift amplifies panic — if your map is wrong, you panic more
    drift_amplifier = 1 + (drift_score / 100)

    # Panic order multiplier
    panic_multiplier = round(base_panic * drift_amplifier * HOARD_MULTIPLIER, 2)

    # Demand spike %
    demand_spike_pct = round((panic_multiplier - 1) * 100, 1)

    # How many companies switch supplier simultaneously
    simultaneous_switchers_pct = round(SIMULTANEOUS_SWITCH * disruption["impact_score"] * 100, 1)

    # Capacity overload — when demand spikes beyond supplier capacity
    capacity_overload = panic_multiplier > 1.8

    return {
        "panic_multiplier":           panic_multiplier,
        "demand_spike_pct":           demand_spike_pct,
        "simultaneous_switchers_pct": simultaneous_switchers_pct,
        "capacity_overload":          capacity_overload,
        "hoarding_weeks":             round(RECOVERY_WEEKS * disruption["impact_score"]),
    }

def simulate_cascade_failure(disruption, suppliers, hidden_deps):
    """
    Simulate how a disruption propagates through the network
    tier by tier — including through hidden dependencies.
    """
    timeline = []
    week = 0

    # Week 0: Disruption hits
    timeline.append({
        "week": week,
        "event": f"{disruption['event_type'].title()} disruption detected",
        "tier_affected": "Origin",
        "visibility": "invisible",
        "action_available": True,
        "note": "ASCNS detects signal — window to act is NOW"
    })

    # Week 1-2: Hidden tiers affected first (invisible to ERP)
    week += 2
    timeline.append({
        "week": week,
        "event": f"{len(hidden_deps)} hidden Tier-3 suppliers impacted",
        "tier_affected": "Tier 3 (hidden)",
        "visibility": "invisible",
        "action_available": True,
        "note": "ERP shows nothing. ASCNS sees this through Shadow Graph."
    })

    # Week 3-4: Tier 2 starts feeling pressure
    week += 2
    timeline.append({
        "week": week,
        "event": "Tier-2 suppliers report lead time increases",
        "tier_affected": "Tier 2",
        "visibility": "partial",
        "action_available": True,
        "note": "Alternative sourcing still available — act now"
    })

    # Week 5-6: Panic ordering begins
    week += 2
    timeline.append({
        "week": week,
        "event": "Market-wide panic ordering begins",
        "tier_affected": "Market",
        "visibility": "visible",
        "action_available": False,
        "note": "⚠ Too late to switch suppliers — all alternatives flooded"
    })

    # Week 7-8: Tier 1 impact visible
    week += 2
    timeline.append({
        "week": week,
        "event": "Tier-1 suppliers miss delivery commitments",
        "tier_affected": "Tier 1",
        "visibility": "visible",
        "action_available": False,
        "note": "Costs have surged 40-80%. Recovery window closed."
    })

    # Week 9+: Recovery
    week += disruption["duration_weeks"]
    timeline.append({
        "week": week,
        "event": "Supply chain begins stabilizing",
        "tier_affected": "All tiers",
        "visibility": "visible",
        "action_available": True,
        "note": "Full recovery. Audit declared vs actual network."
    })

    return timeline

def calculate_financial_impact(disruption, panic, suppliers_count):
    """Estimate financial impact of the disruption + panic cascade."""
    base_revenue_at_risk = suppliers_count * 150000  # avg $150k per supplier relationship
    disruption_loss      = base_revenue_at_risk * disruption["impact_score"]
    panic_amplification  = disruption_loss * (panic["panic_multiplier"] - 1)
    total_loss           = disruption_loss + panic_amplification

    return {
        "base_revenue_at_risk_usd": round(base_revenue_at_risk),
        "disruption_loss_usd":      round(disruption_loss),
        "panic_amplification_usd":  round(panic_amplification),
        "total_estimated_loss_usd": round(total_loss),
        "panic_makes_it_worse_by":  f"{round((panic_amplification/disruption_loss)*100)}%"
    }

def run_full_simulation(event_type="geopolitical", severity=3):
    """
    Run the complete behavioral amplification simulation.
    This is the core ASCNS prediction engine.
    """
    print("\n" + "="*60)
    print("   ASCNS BEHAVIORAL AMPLIFICATION SIMULATION")
    print("="*60)

    # Get current state
    drift      = calculate_drift_score()
    hidden     = get_undeclared_dependencies()
    suppliers  = get_all_suppliers()
    drift_score= drift["drift_score"]

    print(f"\n Current Drift Score: {drift_score}% ({drift['level']})")
    print(f" Hidden Dependencies: {len(hidden)}")
    print(f" Total Suppliers:     {len(suppliers)}")

    # Classify disruption
    disruption = classify_disruption(event_type, severity)
    print(f"\n DISRUPTION EVENT: {event_type.upper()} (Severity {severity}/5)")
    print(f" Impact Score:    {disruption['impact_score']}")
    print(f" Speed:           {disruption['speed']}")
    print(f" Duration:        {disruption['duration_weeks']} weeks")

    # Panic ordering simulation
    panic = simulate_panic_ordering(disruption, drift_score)
    print(f"\n PANIC ORDERING SIMULATION:")
    print(f" Demand spike:              +{panic['demand_spike_pct']}%")
    print(f" Panic multiplier:          {panic['panic_multiplier']}x")
    print(f" Simultaneous switchers:    {panic['simultaneous_switchers_pct']}% of market")
    print(f" Capacity overload:         {'YES ⚠' if panic['capacity_overload'] else 'No'}")
    print(f" Hoarding duration:         {panic['hoarding_weeks']} weeks")

    # Cascade timeline
    timeline = simulate_cascade_failure(disruption, suppliers, hidden)
    print(f"\n CASCADE FAILURE TIMELINE:")
    print("-"*60)
    for event in timeline:
        visibility_icon = "👁" if event["visibility"] == "visible" else "🔴" if event["visibility"] == "invisible" else "⚡"
        action_icon     = "✅ ACT" if event["action_available"] else "❌ LATE"
        print(f"  Week {event['week']:>2} | {visibility_icon} {event['event']}")
        print(f"         | {action_icon} — {event['note']}")
        print()

    # Financial impact
    financial = calculate_financial_impact(disruption, panic, len(suppliers))
    print(f" FINANCIAL IMPACT ESTIMATE:")
    print(f" Base revenue at risk: ${financial['base_revenue_at_risk_usd']:,}")
    print(f" Disruption loss:      ${financial['disruption_loss_usd']:,}")
    print(f" Panic amplification:  ${financial['panic_amplification_usd']:,}")
    print(f" TOTAL ESTIMATED LOSS: ${financial['total_estimated_loss_usd']:,}")
    print(f" Panic makes it worse by: {financial['panic_makes_it_worse_by']}")

    print("\n" + "="*60)

    return {
        "disruption":   disruption,
        "drift_score":  drift_score,
        "panic":        panic,
        "timeline":     timeline,
        "financial":    financial,
        "hidden_count": len(hidden),
        "simulated_at": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Test with a geopolitical disruption, severity 3
    result = run_full_simulation("geopolitical", 3)
    print("\n Also simulating pandemic scenario...")
    run_full_simulation("pandemic", 4)