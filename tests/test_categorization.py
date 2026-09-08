"""
Unit and integration tests for the categorization engine.
Validates:
  1. Master taxonomy depth <= 4, valid parents, unique IDs.
  2. Feed loaders for 2xu XML and Adlibris JSON.
  3. 100% categorization coverage (0 unmapped products).
  4. Correct attribution (gender, category paths).
  5. Zero-touch auto-mapping for arbitrary new merchant feeds.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.taxonomy import Taxonomy
from app.feed_loaders import load_adtraction_xml, load_tradedoubler_json
from app.mapper import CategoryMapper


def test_taxonomy_integrity():
    tax = Taxonomy()
    assert len(tax.all_categories()) > 0
    assert tax.max_depth == 4
    for node in tax.all_categories():
        assert node.level <= 4, f"Node {node.id} exceeds level 4: level={node.level}"
        if node.parent_id:
            assert tax.get(node.parent_id) is not None, f"Parent {node.parent_id} not found"
    print("[OK] test_taxonomy_integrity passed")


def test_feed_mapping_coverage():
    tax = Taxonomy()
    mapper = CategoryMapper(tax)
    
    xml_file = Path(__file__).parent.parent / "2xu__adtraction__2674__2026-09-07T13-22-18-596Z.xml"
    json_file = Path(__file__).parent.parent / "adlibris__tradedoubler__110179__2026-09-01T09-17-38-486Z.json"
    
    prods_2xu = load_adtraction_xml(xml_file, "2xu")
    prods_ad = load_tradedoubler_json(json_file, "adlibris")
    
    assert len(prods_2xu) == 4125, f"Expected 4125 2xu products, got {len(prods_2xu)}"
    assert len(prods_ad) == 2384, f"Expected 2384 Adlibris products, got {len(prods_ad)}"
    
    all_prods = prods_2xu + prods_ad
    mapper.map_batch(all_prods)
    
    unmapped = [p for p in all_prods if not p.category_id]
    invalid_nodes = [p for p in all_prods if not tax.get(p.category_id)]
    too_deep = [p for p in all_prods if tax.get(p.category_id).level > 4]
    
    assert len(unmapped) == 0, f"Found {len(unmapped)} unmapped products!"
    assert len(invalid_nodes) == 0, f"Found {len(invalid_nodes)} invalid category nodes!"
    assert len(too_deep) == 0, f"Found {len(too_deep)} nodes deeper than level 4!"
    
    print(f"[OK] test_feed_mapping_coverage passed: {len(all_prods)} products mapped with 100% coverage")


def test_zero_touch_auto_mapper():
    tax = Taxonomy()
    mapper = CategoryMapper(tax)
    
    cases = [
        ("Dammode > Traning > Kompressionstights", "Lopning Tights Dam", "sport-traning/traningsklader/dam/tights"),
        ("Sallskapsspel > Bradspel for hela familjen", "Ubongo Bradspel", "leksaker-spel/sallskapsspel/bradspel/familjespel"),
        ("Klassiska Tradgardsspel", "Kubb Family Set", "leksaker-spel/utomhuslek/klassiska-utespel/kubb-kastspel"),
        ("Bad & Vatdrakter", "Neopren Vatdrakt", "sport-traning/traningsklader/vatdrakter-simklader/vatdrakter"),
        ("Elektronik > Horlurar", "Tradlosa In-ear Horlurar", "elektronik-teknik/ljud-bild/horlurar/tradlosa"),
        ("Kok > Stekpannor", "Gjutjarnspanna 28cm", "hem-inredning/kok-servering/kokskarl/stekpannor"),
    ]
    
    for cat, title, expected_id in cases:
        res = mapper.simulate_match(source_category=cat, title=title, merchant="NyTestbutik")
        target_id = res["result"]["target_category_id"]
        assert target_id == expected_id, f"Expected '{cat}' -> '{expected_id}', got '{target_id}'"
        assert res["result"]["confidence"] >= 0.50
        
    print("[OK] test_zero_touch_auto_mapper passed for unseen categories")


if __name__ == "__main__":
    test_taxonomy_integrity()
    test_feed_mapping_coverage()
    test_zero_touch_auto_mapper()
    print("\nALL TESTS PASSED SUCCESSFULLY!")
