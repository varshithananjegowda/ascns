from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.graph.models import (
    create_supplier, create_declared_relationship,
    create_inferred_relationship, get_all_suppliers,
    get_supplier_dependencies, get_hidden_concentrations,
)
from src.inference.drift_engine import (
    calculate_drift_score, get_undeclared_dependencies,
    get_tier_drift_breakdown,
)
from src.simulation.panic_model import run_full_simulation
from src.simulation.decision_engine import run_decision_engine
from src.simulation.autonomous_response import run_autonomous_response
from src.ingestion.postgres_module import (
    log_market_signal, get_recent_signals,
    get_high_severity_signals, get_disruption_history,
    get_risk_trend, get_audit_log,
    get_suppliers_from_postgres, save_risk_snapshot
)

router = APIRouter()

class SupplierCreate(BaseModel):
    supplier_id: str
    name: str
    country: str
    tier: int
    industry: str

class DeclaredLink(BaseModel):
    from_id: str
    to_id: str
    product: str
    value_usd: float

class InferredLink(BaseModel):
    from_id: str
    to_id: str
    product: str
    probability: float

class SimulationRequest(BaseModel):
    event_type: str = "geopolitical"
    severity: int = 3

class SignalCreate(BaseModel):
    signal_type: str
    source: str
    affected_country: str
    affected_industry: str
    severity: float
    description: str

@router.get("/health")
def health_check():
    return {"status": "healthy", "system": "ASCNS"}

@router.get("/suppliers")
def list_suppliers():
    try:
        suppliers = get_all_suppliers()
        return {"count": len(suppliers), "suppliers": suppliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suppliers")
def add_supplier(data: SupplierCreate):
    try:
        result = create_supplier(data.supplier_id, data.name, data.country, data.tier, data.industry)
        return {"message": "Supplier created", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suppliers/{supplier_id}/dependencies")
def supplier_dependencies(supplier_id: str):
    try:
        deps = get_supplier_dependencies(supplier_id)
        return {"supplier_id": supplier_id, "dependencies": deps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suppliers/postgres/all")
def list_suppliers_postgres():
    try:
        suppliers = get_suppliers_from_postgres()
        return {"count": len(suppliers), "suppliers": suppliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/declared")
def add_declared_link(data: DeclaredLink):
    try:
        result = create_declared_relationship(data.from_id, data.to_id, data.product, data.value_usd)
        return {"message": "Declared link created", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/inferred")
def add_inferred_link(data: InferredLink):
    try:
        result = create_inferred_relationship(data.from_id, data.to_id, data.product, data.probability)
        return {"message": "Inferred link created", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risks/concentrations")
def hidden_concentrations():
    try:
        risks = get_hidden_concentrations()
        return {"count": len(risks), "chokepoints": risks, "alert": "HIGH" if risks else "NONE"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risks/drift")
def drift_score():
    try:
        return calculate_drift_score()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risks/hidden-dependencies")
def hidden_dependencies():
    try:
        hidden = get_undeclared_dependencies()
        tier_drift = get_tier_drift_breakdown()
        return {"count": len(hidden), "hidden_dependencies": hidden, "tier_breakdown": tier_drift}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risks/trend")
def risk_trend():
    try:
        return {"trend": get_risk_trend(30)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate/disruption")
def simulate_disruption(data: SimulationRequest):
    try:
        return run_full_simulation(data.event_type, data.severity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/simulate/disruption/quick")
def quick_simulation():
    try:
        return run_full_simulation("geopolitical", 3)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/decisions")
def get_decisions():
    try:
        return run_decision_engine()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/autonomous/run")
def run_autonomous():
    try:
        return run_autonomous_response()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/recent")
def recent_signals():
    try:
        return {"signals": get_recent_signals(10)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/high-severity")
def high_severity_signals():
    try:
        return {"signals": get_high_severity_signals(0.7)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/signals")
def add_signal(data: SignalCreate):
    try:
        signal_id = log_market_signal(
            data.signal_type, data.source, data.affected_country,
            data.affected_industry, data.severity, data.description
        )
        return {"message": "Signal logged", "id": signal_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/disruptions/history")
def disruption_history():
    try:
        return {"history": get_disruption_history(10)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit/log")
def audit_log():
    try:
        return {"log": get_audit_log(20)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))