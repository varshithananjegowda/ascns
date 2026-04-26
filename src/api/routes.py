from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.graph.models import (
    create_supplier,
    create_declared_relationship,
    create_inferred_relationship,
    get_all_suppliers,
    get_supplier_dependencies,
    get_hidden_concentrations,
)
from src.inference.drift_engine import (
    calculate_drift_score,
    get_undeclared_dependencies,
    get_tier_drift_breakdown,
)
from src.simulation.panic_model import run_full_simulation
from src.simulation.decision_engine import run_decision_engine

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