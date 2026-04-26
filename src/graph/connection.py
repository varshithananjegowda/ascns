from neo4j import GraphDatabase
from dotenv import load_dotenv
import psycopg2
import os

load_dotenv()

# ── PostgreSQL ──────────────────────────────────────────────
def get_postgres_connection():
    """Returns a PostgreSQL connection."""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# ── Neo4j ───────────────────────────────────────────────────
class Neo4jConnection:
    _driver = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI"),
                auth=(
                    os.getenv("NEO4J_USERNAME"),
                    os.getenv("NEO4J_PASSWORD")
                )
            )
        return cls._driver

    @classmethod
    def close(cls):
        if cls._driver:
            cls._driver.close()
            cls._driver = None

    @classmethod
    def run_query(cls, query, parameters=None):
        """Run a Cypher query and return results."""
        driver = cls.get_driver()
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":
    # Test PostgreSQL
    conn = get_postgres_connection()
    print("PostgreSQL Connected!")
    conn.close()

    # Test Neo4j
    Neo4jConnection.get_driver()
    print("Neo4j Connected!")
    Neo4jConnection.close()

    print("All database connections OK!")