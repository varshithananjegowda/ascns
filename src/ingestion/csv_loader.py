import pandas as pd
import uuid
import os
from src.graph.connection import get_postgres_connection
from src.graph.models import create_supplier, create_declared_relationship

# ── CSV DATA LOADER ───────────────────────────────────────────────────────────
# Loads real supplier data from a CSV file into:
#   1. PostgreSQL — for structured queries and reporting
#   2. Neo4j      — for graph analysis and dependency detection
# ─────────────────────────────────────────────────────────────────────────────

def clean_value(val, default=None):
    """Clean a value from CSV — handle NaN, empty strings."""
    if pd.isna(val) or val == '' or val is None:
        return default
    return val

def generate_supplier_id(name, index):
    """Generate a unique supplier ID from name."""
    clean = ''.join(c for c in str(name) if c.isalnum())[:6].upper()
    return f"SUP{clean}{index:03d}"

def detect_tier(row):
    """
    Infer supplier tier from available data.
    Tier 0 = your company
    Tier 1 = direct suppliers
    Tier 2 = suppliers' suppliers
    Tier 3 = deep supply chain
    """
    if 'tier' in row and pd.notna(row.get('tier')):
        return int(row['tier'])

    # Infer from lead time — longer lead time = deeper tier
    lead_time = row.get('lead_time_days', 0) or row.get('Lead time', 0) or 0
    try:
        lead_time = float(lead_time)
    except:
        lead_time = 0

    if lead_time <= 7:
        return 1
    elif lead_time <= 21:
        return 2
    else:
        return 3

def load_csv_to_postgres(filepath):
    """Load CSV supplier data into PostgreSQL."""
    print(f"\nLoading CSV from: {filepath}")

    df = pd.read_csv(filepath)
    print(f"Found {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    print(f"Normalized columns: {list(df.columns)}")

    conn = get_postgres_connection()
    cur  = conn.cursor()
    loaded = 0
    skipped = 0

    for idx, row in df.iterrows():
        try:
            # Map columns flexibly — handle different CSV formats
            name = (
                clean_value(row.get('supplier_name')) or
                clean_value(row.get('supplier')) or
                clean_value(row.get('name')) or
                f"Supplier_{idx}"
            )

            country = (
                clean_value(row.get('country')) or
                clean_value(row.get('origin')) or
                clean_value(row.get('location')) or
                'Unknown'
            )

            industry = (
                clean_value(row.get('industry')) or
                clean_value(row.get('category')) or
                clean_value(row.get('product_type')) or
                clean_value(row.get('type')) or
                'General'
            )

            product = (
                clean_value(row.get('product')) or
                clean_value(row.get('product_name')) or
                clean_value(row.get('item')) or
                clean_value(row.get('sku')) or
                'Various'
            )

            lead_time = (
                clean_value(row.get('lead_time_days'), 0) or
                clean_value(row.get('lead_time'), 0) or
                clean_value(row.get('lead_times'), 0) or
                0
            )

            annual_value = (
                clean_value(row.get('annual_value'), 0) or
                clean_value(row.get('revenue_generated'), 0) or
                clean_value(row.get('price'), 0) or
                clean_value(row.get('order_quantities'), 0) or
                0
            )

            supplier_id = generate_supplier_id(name, idx)
            tier = detect_tier(row)

            # Insert into PostgreSQL
            cur.execute("""
                INSERT INTO suppliers
                    (supplier_id, name, country, tier, industry,
                     product, lead_time_days, annual_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (supplier_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    country = EXCLUDED.country
            """, (
                supplier_id,
                str(name)[:200],
                str(country)[:100],
                tier,
                str(industry)[:100],
                str(product)[:200],
                float(lead_time) if lead_time else 0,
                float(annual_value) if annual_value else 0
            ))
            loaded += 1

        except Exception as e:
            skipped += 1
            if skipped <= 3:
                print(f"  Skipped row {idx}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nPostgreSQL: {loaded} suppliers loaded, {skipped} skipped")
    return loaded

def load_csv_to_neo4j(filepath, limit=50):
    """
    Load CSV supplier data into Neo4j graph.
    Limit to 50 suppliers to avoid overwhelming free tier.
    Creates nodes and infers relationships from shared countries/industries.
    """
    print(f"\nLoading into Neo4j graph (limit: {limit} suppliers)...")

    df = pd.read_csv(filepath)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    df = df.head(limit)

    loaded = 0
    relationships = 0

    # Track suppliers by country+industry for relationship inference
    country_industry_map = {}

    for idx, row in df.iterrows():
        try:
            name = (
                clean_value(row.get('supplier_name')) or
                clean_value(row.get('supplier')) or
                clean_value(row.get('name')) or
                f"Supplier_{idx}"
            )

            country = (
                clean_value(row.get('country')) or
                clean_value(row.get('origin')) or
                'Unknown'
            )

            industry = (
                clean_value(row.get('industry')) or
                clean_value(row.get('category')) or
                clean_value(row.get('type')) or
                'General'
            )

            supplier_id = generate_supplier_id(name, idx)
            tier = detect_tier(row)

            # Create node in Neo4j
            create_supplier(supplier_id, str(name), str(country), tier, str(industry))

            # Track for relationship inference
            key = f"{country}_{industry}"
            if key not in country_industry_map:
                country_industry_map[key] = []
            country_industry_map[key].append((supplier_id, tier))

            loaded += 1

        except Exception as e:
            if idx < 3:
                print(f"  Neo4j skip row {idx}: {e}")

    print(f"Neo4j: {loaded} supplier nodes created")

    # Infer declared relationships from tier structure
    print("Inferring supply relationships from tier structure...")
    from src.graph.models import create_declared_relationship

    # Connect lower tiers to higher tiers in same industry/country
    for key, suppliers in country_industry_map.items():
        tier1 = [s for s in suppliers if s[1] == 1]
        tier2 = [s for s in suppliers if s[1] == 2]
        tier3 = [s for s in suppliers if s[1] == 3]

        # Tier 1 → Tier 2 connections
        for t1 in tier1[:2]:
            for t2 in tier2[:2]:
                try:
                    create_declared_relationship(t1[0], t2[0], key.split('_')[1], 50000)
                    relationships += 1
                except:
                    pass

        # Tier 2 → Tier 3 connections
        for t2 in tier2[:2]:
            for t3 in tier3[:1]:
                try:
                    create_declared_relationship(t2[0], t3[0], key.split('_')[1], 25000)
                    relationships += 1
                except:
                    pass

    print(f"Created {relationships} supply relationships in Neo4j")
    return loaded

def run_full_load(filepath=None):
    """Run the complete data loading pipeline."""
    if filepath is None:
        filepath = os.path.join('data', 'suppliers.csv')

    if not os.path.exists(filepath):
        print(f"ERROR: File not found at {filepath}")
        print("Please place your suppliers.csv in the data/ folder")
        return

    print("="*60)
    print("   ASCNS DATA LOADER")
    print("="*60)

    # Load to PostgreSQL
    pg_count = load_csv_to_postgres(filepath)

    # Load to Neo4j
    neo4j_count = load_csv_to_neo4j(filepath, limit=50)

    # Log the load event
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_log (action, details)
            VALUES (%s, %s)
        """, (
            'CSV_DATA_LOAD',
            f'Loaded {pg_count} suppliers to PostgreSQL, {neo4j_count} to Neo4j from {filepath}'
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")

    print("\n" + "="*60)
    print(f"Data load complete!")
    print(f"  PostgreSQL: {pg_count} suppliers")
    print(f"  Neo4j:      {neo4j_count} supplier nodes")
    print("="*60)

if __name__ == "__main__":
    run_full_load()