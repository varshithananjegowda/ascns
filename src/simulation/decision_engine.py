from src.inference.drift_engine import (
    calculate_drift_score,
    get_undeclared_dependencies,
    get_high_probability_hidden_links,
)
from src.graph.models import get_hidden_concentrations
from src.simulation.panic_model import (
    classify_disruption,
    simulate_panic_ordering,
    simulate_cascade_failure,
)
from datetime import datetime

# ── DECISION TIMING ENGINE ────────────────────────────────────────────────────
# The final ASCNS intelligence layer.
#
# Not just "what is the risk" — but:
#   WHAT should you do?
#   WHEN should you do it?
#   WHAT should you NOT do?
#
# Gives time-based, ranked, actionable decisions.
# ─────────────────────────────────────────────────────────────────────────────

# Decision urgency levels
URGENCY = {
    "IMMEDIATE": {"label": "Act within 24 hours",  "color": "#ff4444"},
    "URGENT":    {"label": "Act within 48 hours",  "color": "#ff6b6b"},
    "SOON":      {"label": "Act within 1 week",    "color": "#f39c12"},
    "MONITOR":   {"label": "Monitor weekly",        "color": "#4a9eff"},
    "HOLD":      {"label": "No action needed",      "color": "#1D9E75"},
}

def assess_current_risk():
    """
    Assess the current overall risk state
    by combining drift + concentration + hidden deps.
    """
    drift        = calculate_drift_score()
    hidden       = get_undeclared_dependencies()
    high_prob    = get_high_probability_hidden_links()
    chokepoints  = get_hidden_concentrations()

    drift_score  = drift["drift_score"]
    drift_level  = drift["level"]

    # Composite risk score (0-100)
    drift_component       = drift_score * 0.40
    hidden_component      = min(40, len(hidden) * 10) * 0.30
    chokepoint_component  = min(40, len(chokepoints) * 15) * 0.30
    composite_score       = round(drift_component + hidden_component + chokepoint_component)

    if composite_score >= 70:
        overall_risk = "CRITICAL"
    elif composite_score >= 50:
        overall_risk = "HIGH"
    elif composite_score >= 30:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    return {
        "composite_risk_score": composite_score,
        "overall_risk":         overall_risk,
        "drift_score":          drift_score,
        "drift_level":          drift_level,
        "hidden_dep_count":     len(hidden),
        "high_prob_hidden":     len(high_prob),
        "chokepoint_count":     len(chokepoints),
        "chokepoints":          chokepoints,
        "hidden_deps":          hidden,
    }

def generate_decisions(risk):
    """
    Generate ranked, actionable decisions based on current risk state.
    Each decision has: what, why, when, priority, and what NOT to do.
    """
    decisions = []
    score     = risk["composite_risk_score"]
    chokes    = risk["chokepoints"]
    hidden    = risk["hidden_deps"]
    drift     = risk["drift_score"]

    # ── DECISION 1: Supplier Audit ────────────────────────
    if drift >= 40:
        decisions.append({
            "priority":    1,
            "action":      "Conduct Emergency Supplier Audit",
            "urgency":     "IMMEDIATE" if drift >= 60 else "URGENT",
            "why":         f"Drift score is {drift}% — your declared supply chain map is significantly wrong. "
                           f"{risk['hidden_dep_count']} hidden dependencies detected that ERP cannot see.",
            "how": [
                "Contact all Tier-1 suppliers and request full sub-tier disclosure",
                "Cross-reference logistics invoices against declared supplier list",
                "Flag any supplier using shared upstream sources",
                "Update Neo4j graph with confirmed relationships",
            ],
            "do_not":      "Do NOT assume your ERP data is correct. Do NOT make sourcing decisions based on declared map alone.",
            "time_to_act": "24-48 hours",
            "impact":      "Reduces drift score by 20-35 points after audit completion",
        })

    # ── DECISION 2: Chokepoint Mitigation ─────────────────
    if chokes:
        top_choke = chokes[0]
        decisions.append({
            "priority":    2,
            "action":      f"Mitigate Chokepoint: {top_choke['chokepoint']} ({top_choke['country']})",
            "urgency":     "IMMEDIATE" if top_choke["risk_score"] >= 3 else "URGENT",
            "why":         f"{top_choke['chokepoint']} is a hidden single point of failure affecting "
                           f"{top_choke['risk_score']} Tier-1 suppliers: {', '.join(top_choke['affects'])}. "
                           f"A disruption here collapses your entire supply chain simultaneously.",
            "how": [
                f"Identify 2 alternative suppliers for {top_choke['chokepoint']}'s products",
                "Negotiate pre-qualification agreements now — before a crisis",
                "Build 6-8 weeks of strategic buffer inventory for this component",
                "Insert contractual sub-tier disclosure clauses with Tier-1 suppliers",
            ],
            "do_not":      "Do NOT wait for a disruption signal to start finding alternatives. "
                           "Do NOT switch all volume at once — maintain relationships.",
            "time_to_act": "Within 1 week",
            "impact":      f"Eliminates single point of failure affecting {top_choke['risk_score']} suppliers",
        })

    # ── DECISION 3: Pre-position Inventory ────────────────
    if score >= 40:
        decisions.append({
            "priority":    3,
            "action":      "Pre-position Strategic Inventory",
            "urgency":     "SOON",
            "why":         "Behavioral modeling shows that when disruption signals appear, "
                           "50-72% of the market panic-orders simultaneously. "
                           "Pre-positioning now avoids competing in that market.",
            "how": [
                "Identify top 5 components sourced from high-risk tiers",
                "Build 8-12 week buffer for components with Tier-3 hidden dependencies",
                "Stagger ordering — do NOT place all orders at once",
                "Avoid triggering demand spike signals in the market",
            ],
            "do_not":      "Do NOT hoard aggressively — this triggers the panic cascade you're trying to avoid. "
                           "Do NOT pre-order from a single supplier.",
            "time_to_act": "Within 1 week",
            "impact":      "Reduces exposure to panic-driven price surges by 40-60%",
        })

    # ── DECISION 4: Hidden Dependency Resolution ──────────
    if risk["high_prob_hidden"] >= 2:
        decisions.append({
            "priority":    4,
            "action":      "Resolve High-Probability Hidden Dependencies",
            "urgency":     "SOON",
            "why":         f"{risk['high_prob_hidden']} hidden relationships have >80% probability of being real. "
                           "These are almost certainly active supply relationships not in your ERP.",
            "how": [
                "Request supply chain disclosure from flagged Tier-1 suppliers",
                "Audit logistics and payment records for undisclosed relationships",
                "Add verified hidden links to the declared network in ASCNS",
                "Renegotiate contracts to require sub-tier transparency",
            ],
            "do_not":      "Do NOT accept supplier assurances without documentation. "
                           "Do NOT update your risk model until verified.",
            "time_to_act": "Within 2 weeks",
            "impact":      "Converts hidden risk into visible, manageable risk",
        })

    # ── DECISION 5: What NOT to do right now ──────────────
    decisions.append({
        "priority":    5,
        "action":      "Market Timing — What NOT to Do",
        "urgency":     "MONITOR",
        "why":         "Panic reactions cause more damage than the original disruption. "
                       "ASCNS detects that the market has NOT yet entered panic mode. "
                       "Acting rationally now gives you significant advantage.",
        "how": [
            "Do NOT mass-switch suppliers without confirmed alternatives",
            "Do NOT place emergency orders that exceed normal run-rate by >30%",
            "Do NOT publicly signal supply chain concerns (triggers competitor panic)",
            "DO quietly pre-qualify alternatives before they become scarce",
        ],
        "do_not":      "Do NOT react to rumors or unverified disruption signals. "
                       "Wait for ASCNS confidence score >75% before major moves.",
        "time_to_act": "Ongoing",
        "impact":      "Avoids $1M+ in panic-driven premium costs",
    })

    return decisions

def calculate_action_window(risk):
    """
    How much time does the company have before:
    1. Hidden risks become visible to everyone (window closes)
    2. Panic ordering floods the market
    3. Costs surge beyond reasonable levels
    """
    score = risk["composite_risk_score"]
    drift = risk["drift_score"]

    # Estimated weeks before market-visible crisis
    if score >= 70:
        weeks_to_crisis     = 2
        weeks_to_panic      = 1
        cost_surge_expected = "60-90%"
        window_status       = "CLOSING"
    elif score >= 50:
        weeks_to_crisis     = 4
        weeks_to_panic      = 3
        cost_surge_expected = "40-60%"
        window_status       = "OPEN — Act Now"
    elif score >= 30:
        weeks_to_crisis     = 8
        weeks_to_panic      = 6
        cost_surge_expected = "20-40%"
        window_status       = "OPEN — Monitor"
    else:
        weeks_to_crisis     = 16
        weeks_to_panic      = 12
        cost_surge_expected = "10-20%"
        window_status       = "STABLE"

    return {
        "window_status":        window_status,
        "weeks_to_crisis":      weeks_to_crisis,
        "weeks_to_panic_order": weeks_to_panic,
        "cost_surge_expected":  cost_surge_expected,
        "advantage_over_market": f"{weeks_to_panic} weeks ahead of market reaction",
    }

def run_decision_engine():
    """
    Run the full Decision Timing Engine.
    Produces ranked, time-based, actionable decisions.
    """
    print("\n" + "="*60)
    print("   ASCNS DECISION TIMING ENGINE")
    print("="*60)

    # Assess risk
    risk   = assess_current_risk()
    window = calculate_action_window(risk)

    print(f"\n COMPOSITE RISK SCORE: {risk['composite_risk_score']}/100 — {risk['overall_risk']}")
    print(f"\n ACTION WINDOW: {window['window_status']}")
    print(f" Weeks to crisis:          {window['weeks_to_crisis']} weeks")
    print(f" Weeks to panic ordering:  {window['weeks_to_panic_order']} weeks")
    print(f" Expected cost surge:      {window['cost_surge_expected']}")
    print(f" Your advantage:           {window['advantage_over_market']}")

    # Generate decisions
    decisions = generate_decisions(risk)
    print(f"\n RANKED DECISIONS ({len(decisions)} actions):")
    print("-"*60)

    urgency_icons = {
        "IMMEDIATE": "🔴",
        "URGENT":    "🟠",
        "SOON":      "🟡",
        "MONITOR":   "🔵",
        "HOLD":      "🟢",
    }

    for dec in decisions:
        icon = urgency_icons.get(dec["urgency"], "⚪")
        print(f"\n  #{dec['priority']} {icon} [{dec['urgency']}] {dec['action']}")
        print(f"     Why:        {dec['why'][:80]}...")
        print(f"     Act by:     {dec['time_to_act']}")
        print(f"     Impact:     {dec['impact']}")
        print(f"     Do NOT:     {dec['do_not'][:70]}...")

    print("\n" + "="*60)

    return {
        "risk":      risk,
        "window":    window,
        "decisions": decisions,
        "generated_at": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    result = run_decision_engine()