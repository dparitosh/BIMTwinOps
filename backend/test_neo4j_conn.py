"""Quick Neo4j connection test"""
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_USER = os.getenv("NEO4J_USER", "")
NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

from neo4j import GraphDatabase

def test():
    print(f"Testing direct Neo4j connection to {NEO4J_URI} (database={NEO4J_DATABASE})...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("MATCH (n) RETURN count(n) as total")
            record = result.single()
            print(f"Node count: {record['total']}")
        driver.close()
        print("Neo4j connection successful!")
        return True
    except Exception as e:
        print(f"Neo4j connection failed: {e}")
        return False

if __name__ == "__main__":
    test()
