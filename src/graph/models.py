from src.graph.connection import Neo4jConnection, get_postgres_connection
from datetime import datetime

# ── SUPPLIER NODES ────────────────────────────────────────────────────────────

def create_supplier(supplier_id, name, country, tier, industry):
    """Create a supplier node in the graph."""
    query = """
    MERGE (s:Supplier {supplier_id: $supplier_id})
    SET s.name = $name,
        s.country = $country,
        s.tier = $tier,
        s.industry = $industry,
        s.created_at = $created_at
    RETURN s
    """
    result = Neo4jConnection.run_query(query, {
        "supplier_id": supplier_id,
        "name": name,
        "country": country,
        "tier": tier,
        "industry": industry,
        "created_at": datetime.utcnow().isoformat()
    })
    print(f"Created supplier: {name} (Tier {tier}, {country})")
    return result

# ── RELATIONSHIPS ─────────────────────────────────────────────────────────────

def create_declared_relationship(from_id, to_id, product, value_usd):
    """
    Declared relationship — what ERP/contracts say.
    A -> B means A buys from B.
    """
    query = """
    MATCH (a:Supplier {supplier_id: $from_id})
    MATCH (b:Supplier {supplier_id: $to_id})
    MERGE (a)-[r:DECLARED_SUPPLIES {product: $product}]->(b)
    SET r.value_usd = $value_usd,
        r.type = 'declared',
        r.updated_at = $updated_at
    RETURN r
    """
    result = Neo4jConnection.run_query(query, {
        "from_id": from_id,
        "to_id": to_id,
        "product": product,
        "value_usd": value_usd,
        "updated_at": datetime.utcnow().isoformat()
    })
    print(f"Declared link: {from_id} → {to_id} ({product})")
    return result

def create_inferred_relationship(from_id, to_id, product, probability):
    """
    Inferred relationship — what ASCNS detects as likely real.
    This is the Shadow Supply Graph layer.
    """
    query = """
    MATCH (a:Supplier {supplier_id: $from_id})
    MATCH (b:Supplier {supplier_id: $to_id})
    MERGE (a)-[r:INFERRED_SUPPLIES {product: $product}]->(b)
    SET r.probability = $probability,
        r.type = 'inferred',
        r.updated_at = $updated_at
    RETURN r
    """
    result = Neo4jConnection.run_query(query, {
        "from_id": from_id,
        "to_id": to_id,
        "product": product,
        "probability": probability,
        "updated_at": datetime.utcnow().isoformat()
    })
    print(f"Inferred link: {from_id} → {to_id} ({product}, prob={probability})")
    return result

# ── QUERY THE GRAPH ───────────────────────────────────────────────────────────

def get_all_suppliers():
    """Get all suppliers in the graph."""
    query = "MATCH (s:Supplier) RETURN s ORDER BY s.tier"
    return Neo4jConnection.run_query(query)

def get_supplier_dependencies(supplier_id):
    """Get everything a supplier depends on (declared + inferred)."""
    query = """
    MATCH (s:Supplier {supplier_id: $supplier_id})-[r]->(dep:Supplier)
    RETURN s.name as supplier, type(r) as link_type,
           dep.name as depends_on, dep.country as country,
           dep.tier as tier
    ORDER BY dep.tier
    """
    return Neo4jConnection.run_query(query, {"supplier_id": supplier_id})

def get_hidden_concentrations():
    """
    Find suppliers that multiple Tier-1 suppliers depend on
    but through different paths — phantom dependencies.
    """
    query = """
    MATCH (t1:Supplier {tier: 1})-[*1..3]->(shared:Supplier)
    WITH shared, collect(DISTINCT t1.name) as dependent_tier1
    WHERE size(dependent_tier1) > 1
    RETURN shared.name as chokepoint,
           shared.country as country,
           shared.tier as tier,
           dependent_tier1 as affects,
           size(dependent_tier1) as risk_score
    ORDER BY risk_score DESC
    """
    return Neo4jConnection.run_query(query)

# ── SEED SAMPLE DATA ──────────────────────────────────────────────────────────

def seed_sample_data():
    """Load sample supply chain data to test the graph."""
    print("\n Seeding sample supply chain data...")

    # Your company
    create_supplier("OEM001", "AcmeCorp (You)", "India", 0, "Electronics")

    # Tier 1 — direct suppliers
    create_supplier("T1001", "AlphaElec", "Germany", 1, "Electronics")
    create_supplier("T1002", "BetaManuf", "China", 1, "Manufacturing")
    create_supplier("T1003", "GammaParts", "Japan", 1, "Components")

    # Tier 2 — suppliers' suppliers
    create_supplier("T2001", "ChipMaker X", "Taiwan", 2, "Semiconductors")
    create_supplier("T2002", "RareMetals Co", "Congo", 2, "Raw Materials")
    create_supplier("T2003", "PCB Factory", "China", 2, "Electronics")

    # Tier 3 — deep hidden suppliers
    create_supplier("T3001", "LithiumMine A", "Chile", 3, "Mining")
    create_supplier("T3002", "SiliconSource", "China", 3, "Raw Materials")

    print("\n Creating declared relationships...")
    create_declared_relationship("OEM001", "T1001", "Circuit Boards", 500000)
    create_declared_relationship("OEM001", "T1002", "Enclosures", 300000)
    create_declared_relationship("OEM001", "T1003", "Sensors", 200000)
    create_declared_relationship("T1001", "T2001", "Chips", 150000)
    create_declared_relationship("T1002", "T2003", "PCBs", 100000)

    print("\n Creating inferred (hidden) relationships...")
    # ASCNS detects these — not in any ERP
    create_inferred_relationship("T1003", "T2001", "Chips", 0.87)
    create_inferred_relationship("T2001", "T3002", "Silicon", 0.92)
    create_inferred_relationship("T2003", "T3002", "Silicon", 0.78)
    # Hidden concentration: both T2001 and T2003 depend on T3002 (SiliconSource)
    # but OEM001 thinks AlphaElec and BetaManuf are independent!

    print("\n Sample data seeded!")

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Seed data
    seed_sample_data()

    # Show all suppliers
    print("\n All suppliers in graph:")
    suppliers = get_all_suppliers()
    for s in suppliers:
        print(f"  Tier {s['s']['tier']} | {s['s']['name']} ({s['s']['country']})")

    # Show dependencies for AcmeCorp
    print("\n AcmeCorp dependencies:")
    deps = get_supplier_dependencies("OEM001")
    for d in deps:
        print(f"  {d['supplier']} → {d['depends_on']} ({d['link_type']})")

    # Show hidden concentrations
    print("\n Hidden concentration risks (Phantom Dependencies):")
    risks = get_hidden_concentrations()
    if risks:
        for r in risks:
            print(f"  CHOKEPOINT: {r['chokepoint']} ({r['country']})")
            print(f"  Affects: {r['affects']}")
            print(f"  Risk Score: {r['risk_score']}")
    else:
        print("  None detected yet")