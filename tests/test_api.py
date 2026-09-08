"""
API and integration tests for FastAPI application endpoints.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def test_api():
    with TestClient(app) as client:
        # 1. Health
        r = client.get('/health')
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        print("[OK] /health endpoint")

    # 2. Category tree
    r = client.get('/api/tree')
    assert r.status_code == 200
    tree_data = r.json()
    assert tree_data["max_depth"] == 4
    assert tree_data["total_categories"] > 0
    print(f"[OK] /api/tree ({tree_data['total_categories']} categories)")

    # 3. Products list & pagination
    r = client.get('/api/products?limit=10')
    assert r.status_code == 200
    p_data = r.json()
    assert p_data["total"] == 6509
    assert len(p_data["items"]) == 10
    print(f"[OK] /api/products ({p_data['total']} total products)")

    # 4. Filter by category
    r = client.get('/api/products?category_id=sport-traning/traningsklader/dam/tights')
    assert r.status_code == 200
    c_data = r.json()
    assert c_data["total"] > 0
    print(f"[OK] Category filter ({c_data['total']} tights found)")

    # 5. Search query
    r = client.get('/api/products?q=kubb')
    assert r.status_code == 200
    q_data = r.json()
    assert q_data["total"] > 0
    print(f"[OK] Search query 'kubb' ({q_data['total']} matches)")

    # 6. Simulator
    sim_payload = {
        "source_category": "Dammode > Traning > Kompressionstights",
        "title": "Nike Pro Tights Dam",
        "merchant": "Stadium",
        "gender": "Dam"
    }
    r = client.post('/api/simulate', json=sim_payload)
    assert r.status_code == 200
    s_data = r.json()["result"]
    assert "sport-traning" in s_data["target_category_id"]
    assert s_data["confidence"] >= 0.50
    print(f"[OK] /api/simulate -> {s_data['path_string']} (Rule: {s_data['rule_applied']})")

    # 7. HTML Index page
    r = client.get('/')
    assert r.status_code == 200
    assert "raizemore" in r.text
    print(f"[OK] GET / (HTML presentation page, {len(r.text)} bytes)")

    print("\nALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    test_api()
