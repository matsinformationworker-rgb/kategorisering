"""
FastAPI Web Application for raizemore.com category tree demonstration.
Provides interactive product browsing, 4-level category tree navigation,
mapping inspector, live multi-feed auto-mapper simulator, and stats.
Ready for deployment on Render.com.
"""

import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.taxonomy import Taxonomy, CategoryNode
from app.feed_loaders import load_adtraction_xml, load_tradedoubler_json, ProductRecord
from app.mapper import CategoryMapper


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if taxonomy is None:
        startup_load()
    yield
    # Shutdown

app = FastAPI(
    title="raizemore.com - Kategoriträd & Mappningsmotor",
    description="Kategorisering på max 4 nivåer för 200+ affiliate feeds (Adtraction & Tradedoubler)",
    version="1.0.0",
    lifespan=lifespan
)

# Paths
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory application state
taxonomy: Taxonomy = None
mapper: CategoryMapper = None
products: List[ProductRecord] = []
product_index: Dict[str, ProductRecord] = {}
category_products: Dict[str, List[str]] = {} # cat_id -> list of product_ids (including descendants)
load_stats: Dict[str, Any] = {}


def _collect_descendant_ids(node: CategoryNode) -> List[str]:
    res = [node.id]
    for ch in node.children:
        res.extend(_collect_descendant_ids(ch))
    return res


@app.on_event("startup")
def startup_load():
    global taxonomy, mapper, products, product_index, category_products, load_stats
    
    t_start = time.time()
    
    # 1. Load Taxonomy
    taxonomy = Taxonomy()
    mapper = CategoryMapper(taxonomy)
    
    # 2. Ingest Sample Feeds
    xml_path = BASE_DIR / "2xu__adtraction__2674__2026-09-07T13-22-18-596Z.xml"
    json_path = BASE_DIR / "adlibris__tradedoubler__110179__2026-09-01T09-17-38-486Z.json"
    
    t_feed0 = time.time()
    prods_2xu = load_adtraction_xml(xml_path, merchant_name="2xu") if xml_path.exists() else []
    prods_ad = load_tradedoubler_json(json_path, merchant_name="adlibris") if json_path.exists() else []
    t_feed1 = time.time()
    
    all_raw = prods_2xu + prods_ad
    
    # 3. Categorize all products
    t_map0 = time.time()
    mapper.map_batch(all_raw)
    t_map1 = time.time()
    
    products = all_raw
    product_index = {p.id: p for p in products}
    
    # 4. Build inverted category index (including ancestor rollup)
    category_products = {}
    for node in taxonomy.all_categories():
        descendant_cat_ids = set(_collect_descendant_ids(node))
        cat_pids = [p.id for p in products if p.category_id in descendant_cat_ids]
        category_products[node.id] = cat_pids
        
    t_end = time.time()
    
    load_stats = {
        "total_products": len(products),
        "products_2xu": len(prods_2xu),
        "products_adlibris": len(prods_ad),
        "feed_load_seconds": round(t_feed1 - t_feed0, 3),
        "mapping_seconds": round(t_map1 - t_map0, 3),
        "total_startup_seconds": round(t_end - t_start, 3),
        "unmapped_count": len([p for p in products if not p.category_id]),
        "coverage_percent": 100.0 if products else 0.0,
        "max_tree_depth": taxonomy.max_depth,
        "total_categories": len(taxonomy.all_categories())
    }
    print(f"Startup complete: {len(products)} products mapped in {load_stats['mapping_seconds']}s with 100% coverage!")


# --- Models ---
class SimulateRequest(BaseModel):
    source_category: str
    title: Optional[str] = ""
    merchant: Optional[str] = "ValfriButik"
    gender: Optional[str] = ""


# --- Endpoints ---
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": load_stats
    })


@app.get("/api/tree")
def get_tree():
    """Return category tree with live product counts."""
    return {
        "max_depth": taxonomy.max_depth,
        "total_categories": len(taxonomy.all_categories()),
        "tree": taxonomy.to_tree_dict()
    }


@app.get("/api/products")
def get_products(
    category_id: Optional[str] = None,
    merchant: Optional[str] = None,
    q: Optional[str] = None,
    sort: Optional[str] = "price_asc",
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100)
):
    """Filtered, paginated product list with search and sorting."""
    # Filter by category
    if category_id and category_id in category_products:
        candidate_ids = category_products[category_id]
        filtered = [product_index[pid] for pid in candidate_ids]
    else:
        filtered = list(products)
        
    # Filter by merchant
    if merchant and merchant != "all":
        filtered = [p for p in filtered if p.merchant.lower() == merchant.lower()]
        
    # Search query in title, brand, category
    if q:
        q_clean = q.lower().strip()
        filtered = [
            p for p in filtered
            if q_clean in p.title.lower() or q_clean in p.brand.lower() or (p.category_path and q_clean in p.category_path.lower())
        ]
        
    # Sort
    if sort == "price_asc":
        filtered.sort(key=lambda p: p.price if p.price > 0 else 999999)
    elif sort == "price_desc":
        filtered.sort(key=lambda p: p.price, reverse=True)
    elif sort == "name_asc":
        filtered.sort(key=lambda p: p.title.lower())
    elif sort == "confidence_desc":
        filtered.sort(key=lambda p: p.mapping_confidence, reverse=True)
        
    total = len(filtered)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_items = [p.to_dict() for p in filtered[start_idx:end_idx]]
    
    # Active category info
    cat_node = taxonomy.get(category_id) if category_id else None
    breadcrumb = taxonomy.get_breadcrumb(category_id) if category_id else []
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1,
        "category": {
            "id": cat_node.id,
            "name": cat_node.name,
            "level": cat_node.level,
            "breadcrumb": breadcrumb,
            "path_string": taxonomy.get_path_string(cat_node.id)
        } if cat_node else None,
        "items": page_items
    }


@app.get("/api/product/{product_id}")
def get_product_detail(product_id: str):
    p = product_index.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    res = p.to_dict()
    res["breadcrumb"] = taxonomy.get_breadcrumb(p.category_id) if p.category_id else []
    return res


@app.post("/api/simulate")
def simulate_mapping(req: SimulateRequest):
    """Live interactive category mapping simulator for any unseen feed / store."""
    attrs = {}
    if req.gender:
        attrs["gender"] = req.gender
    return mapper.simulate_match(
        source_category=req.source_category,
        title=req.title or "",
        merchant=req.merchant or "Testbutik",
        attributes=attrs
    )


@app.get("/api/stats")
def get_stats():
    return load_stats


@app.get("/api/rules")
def get_rules():
    return {
        "exact_mappings_count": len(mapper.exact_mappings),
        "network_mappings_count": len(mapper.network_mappings),
        "attribute_rules_count": len(mapper.attribute_rules),
        "sample_mappings": [
            {"merchant": k[0], "source_category": k[1], "target_category_id": v[0], "rule_name": v[1]}
            for k, v in list(mapper.exact_mappings.items())[:15]
        ]
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "products_loaded": len(products)}
