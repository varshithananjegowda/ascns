from src.simulation.decision_engine import assess_current_risk, calculate_action_window
from src.inference.drift_engine import calculate_drift_score
from src.graph.models import get_hidden_concentrations
from src.ingestion.postgres_module import (
    log_action, log_disruption_event,
    save_risk_snapshot, log_market_signal
)
from datetime import datetime

# ── AUTONOMOUS RESPONSE LAYER ─────────────────────────────────────────────────
# The final ASCNS intelligence layer.
#
# When risk thresholds are breached, ASCNS automatically:
#   1. Triggers alerts
#   2. Reallocates sourcing recommendations
#   3. Adjusts procurement strategy
#   4. Avoids market-driven overreaction
#   5. Logs every action for audit
#
# This moves ASCNS from INSIGHT → EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

# Risk thresholds that trigger autonomous actions
THRESHOLDS = {
    "CRITICAL_DRIFT":       70,   # Drift score above this → emergency audit
    "HIGH_COMPOSITE":       60,   # Composite risk above this → sourcing reallocation
    "CHOKEPOINT_RISK":       2,   # More than this many chokepoints → buffer order
    "HIDDEN_DEP_COUNT":      3,   # More than this many hidden deps → disclosure demand
    "PANIC_PREVENTION":     50,   # Composite above this → hold orders, avoid panic
}

def evaluate_thresholds(risk):
    """
    Check which thresholds are breached and
    determine what autonomous actions to trigger.
    """
    triggered = []
    score  = risk["composite_risk_score"]
    drift  = risk["drift_score"]
    chokes = risk["chokepoint_count"]
    hidden = risk["hidden_dep_count"]

    if drift >= THRESHOLDS["CRITICAL_DRIFT"]:
        triggered.append({
            "threshold": "CRITICAL_DRIFT",
            "value":     drift,
            "limit":     THRESHOLDS["CRITICAL_DRIFT"],
            "action":    "EMERGENCY_AUDIT"
        })

    if score >= THRESHOLDS["HIGH_COMPOSITE"]:
        triggered.append({
            "threshold": "HIGH_COMPOSITE",
            "value":     score,
            "limit":     THRESHOLDS["HIGH_COMPOSITE"],
            "action":    "SOURCING_REALLOCATION"
        })

    if chokes >= THRESHOLDS["CHOKEPOINT_RISK"]:
        triggered.append({
            "threshold": "CHOKEPOINT_RISK",
            "value":     chokes,
            "limit":     THRESHOLDS["CHOKEPOINT_RISK"],
            "action":    "BUFFER_INVENTORY_ORDER"
        })

    if hidden >= THRESHOLDS["HIDDEN_DEP_COUNT"]:
        triggered.append({
            "threshold": "HIDDEN_DEP_COUNT",
            "value":     hidden,
            "limit":     THRESHOLDS["HIDDEN_DEP_COUNT"],
            "action":    "SUPPLIER_DISCLOSURE_DEMAND"
        })

    if score >= THRESHOLDS["PANIC_PREVENTION"]:
        triggered.append({
            "threshold": "PANIC_PREVENTION",
            "value":     score,
            "limit":     THRESHOLDS["PANIC_PREVENTION"],
            "action":    "PANIC_PREVENTION_HOLD"
        })

    return triggered

def execute_emergency_audit(risk):
    """Autonomous action: trigger emergency supplier audit."""
    action = {
        "type":        "EMERGENCY_AUDIT",
        "priority":    "IMMEDIATE",
        "description": "Automated emergency audit triggered by critical drift score",
        "steps": [
            "Send automated disclosure requests to all Tier-1 suppliers",
            "Flag all inferred relationships for verification",
            "Suspend new supplier onboarding until audit complete",
            "Generate audit report for procurement team",
        ],
        "estimated_completion": "48-72 hours",
        "expected_outcome":     "Drift score reduction of 20-35 points"
    }
    log_action("EMERGENCY_AUDIT_TRIGGERED",
               f"Drift={risk['drift_score']}% exceeded threshold. Auto-audit initiated.")
    return action

def execute_sourcing_reallocation(risk):
    """Autonomous action: recommend sourcing reallocation."""
    chokepoints = risk.get("chokepoints", [])
    top_choke   = chokepoints[0] if chokepoints else None

    reallocation = []

    if top_choke:
        reallocation.append({
            "from_supplier":  top_choke["chokepoint"],
            "country":        top_choke["country"],
            "risk":           "SINGLE_POINT_OF_FAILURE",
            "recommendation": "Dual-source immediately",
            "volume_shift":   "Move 30% volume to qualified alternative",
            "timeline":       "Within 2 weeks",
        })

    action = {
        "type":           "SOURCING_REALLOCATION",
        "priority":       "URGENT",
        "description":    "Automated sourcing reallocation triggered by high composite risk",
        "reallocations":  reallocation,
        "steps": [
            "Identify qualified alternative suppliers for flagged components",
            "Initiate RFQ process with pre-qualified alternatives",
            "Shift 20-30% of volume — do NOT switch 100% at once",
            "Maintain existing relationships as backup",
        ],
        "estimated_savings": "40-60% reduction in concentration risk",
        "warning": "Do NOT announce supplier switch publicly — triggers market panic"
    }
    log_action("SOURCING_REALLOCATION_TRIGGERED",
               f"Composite risk={risk['composite_risk_score']}/100. Reallocation recommended.")
    return action

def execute_buffer_inventory(risk):
    """Autonomous action: order buffer inventory for chokepoint components."""
    chokepoints = risk.get("chokepoints", [])

    buffer_orders = []
    for choke in chokepoints:
        buffer_orders.append({
            "component":     choke["chokepoint"],
            "current_risk":  choke["risk_score"],
            "buffer_weeks":  8,
            "order_size":    "8-week safety stock",
            "timing":        "Order within 72 hours — before market signal",
            "caution":       "Stagger orders — do NOT place all at once"
        })

    action = {
        "type":          "BUFFER_INVENTORY_ORDER",
        "priority":      "SOON",
        "description":   "Pre-emptive buffer inventory for chokepoint components",
        "buffer_orders": buffer_orders,
        "steps": [
            "Calculate 8-week safety stock for each chokepoint component",
            "Place staggered orders — spread over 2 weeks",
            "Use multiple suppliers to avoid triggering demand spike",
            "Store in geographically distributed warehouses",
        ],
        "cost_estimate":  "2-4% of annual component spend",
        "benefit":        "Avoids 40-80% cost surge during panic phase"
    }
    log_action("BUFFER_INVENTORY_TRIGGERED",
               f"{len(chokepoints)} chokepoints detected. Buffer inventory recommended.")
    return action

def execute_disclosure_demand(risk):
    """Autonomous action: demand sub-tier supplier disclosure."""
    action = {
        "type":        "SUPPLIER_DISCLOSURE_DEMAND",
        "priority":    "SOON",
        "description": f"Automated disclosure demand for {risk['hidden_dep_count']} hidden dependencies",
        "steps": [
            "Generate formal sub-tier disclosure request letters",
            "Send to all Tier-1 suppliers with hidden dependencies",
            "Set 14-day response deadline with contractual backing",
            "Escalate to legal team if no response within 7 days",
        ],
        "template":    "ASCNS-DISCLOSURE-REQUEST-v1",
        "legal_basis": "Supply chain transparency clause in supplier contracts"
    }
    log_action("DISCLOSURE_DEMAND_TRIGGERED",
               f"{risk['hidden_dep_count']} hidden deps detected. Disclosure requested.")
    return action

def execute_panic_prevention(risk):
    """
    Autonomous action: prevent panic ordering.
    ASCNS holds back recommendations to avoid amplifying the crisis.
    """
    action = {
        "type":        "PANIC_PREVENTION_HOLD",
        "priority":    "MONITOR",
        "description": "Market panic prevention mode activated",
        "steps": [
            "HOLD all non-critical order increases above +30% run-rate",
            "BLOCK mass supplier switching requests pending ASCNS approval",
            "Monitor competitor ordering behavior via market signals",
            "Release hold only when ASCNS confidence score >75%",
        ],
        "rationale":   "Panic ordering amplifies disruption by 190-314%. "
                       "ASCNS prevents self-inflicted damage.",
        "duration":    "Until composite risk drops below 40/100"
    }
    log_action("PANIC_PREVENTION_ACTIVATED",
               f"Composite risk={risk['composite_risk_score']}/100. Panic prevention hold active.")
    return action

def run_autonomous_response():
    """
    Main autonomous response engine.
    Assesses current risk, evaluates thresholds,
    and executes appropriate automated responses.
    """
    print("\n" + "="*60)
    print("   ASCNS AUTONOMOUS RESPONSE ENGINE")
    print("="*60)
    print(f"   Running at: {datetime.utcnow().isoformat()}")
    print("="*60)

    # Assess current risk state
    risk   = assess_current_risk()
    window = calculate_action_window(risk)

    print(f"\n Current State:")
    print(f"  Composite Risk:    {risk['composite_risk_score']}/100 ({risk['overall_risk']})")
    print(f"  Drift Score:       {risk['drift_score']}%")
    print(f"  Chokepoints:       {risk['chokepoint_count']}")
    print(f"  Hidden Deps:       {risk['hidden_dep_count']}")
    print(f"  Action Window:     {window['window_status']}")

    # Save risk snapshot to PostgreSQL
    save_risk_snapshot(
        drift_score=risk['drift_score'],
        composite_risk=risk['composite_risk_score'],
        risk_level=risk['overall_risk'],
        hidden_deps=risk['hidden_dep_count'],
        chokepoints=risk['chokepoint_count']
    )

    # Evaluate thresholds
    triggered = evaluate_thresholds(risk)

    if not triggered:
        print("\n No thresholds breached — system stable")
        print(" ASCNS monitoring continues...")
        log_action("AUTONOMOUS_CHECK", "All thresholds within normal range. No action required.")
        return {"status": "STABLE", "actions": [], "risk": risk}

    print(f"\n {len(triggered)} threshold(s) breached — executing responses:")
    print("-"*60)

    # Action dispatch map
    action_map = {
        "EMERGENCY_AUDIT":            execute_emergency_audit,
        "SOURCING_REALLOCATION":      execute_sourcing_reallocation,
        "BUFFER_INVENTORY_ORDER":     execute_buffer_inventory,
        "SUPPLIER_DISCLOSURE_DEMAND": execute_disclosure_demand,
        "PANIC_PREVENTION_HOLD":      execute_panic_prevention,
    }

    executed_actions = []
    for t in triggered:
        action_name = t["action"]
        print(f"\n Executing: {action_name}")
        print(f"  Triggered by: {t['threshold']} = {t['value']} (limit: {t['limit']})")

        if action_name in action_map:
            result = action_map[action_name](risk)
            executed_actions.append(result)

            print(f"  Priority:     {result['priority']}")
            print(f"  Description:  {result['description'][:70]}...")
            print(f"  Steps:")
            for step in result['steps'][:3]:
                print(f"    → {step}")

    print("\n" + "="*60)
    print(f" {len(executed_actions)} autonomous action(s) executed")
    print(f" All actions logged to audit trail")
    print("="*60)

    return {
        "status":           "ACTIONS_EXECUTED",
        "actions_count":    len(executed_actions),
        "actions":          executed_actions,
        "risk":             risk,
        "window":           window,
        "executed_at":      datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    result = run_autonomous_response()