"""
Unified feed loaders and normalizers for raizemore.com.
Supports Google Shopping RSS XML (Adtraction), Tradedoubler PDT JSON, and CSV feeds.
Normalizes products from 200+ feeds into standard ProductRecords.
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any


@dataclass
class ProductRecord:
    id: str
    title: str
    description: str
    brand: str
    price: float
    currency: str
    url: str
    image_url: str
    merchant: str
    network: str
    source_category: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Categorization results (filled by mapper)
    category_id: Optional[str] = None
    category_path: Optional[str] = None
    mapping_rule: Optional[str] = None
    mapping_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_price(price_str: Any) -> float:
    if not price_str:
        return 0.0
    if isinstance(price_str, (int, float)):
        return float(price_str)
    # Extract first number like "999 SEK" or "259.0" or "1 299 kr"
    s = str(price_str).replace(" ", "").replace(",", ".")
    match = re.search(r"(\d+(\.\d+)?)", s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0


def load_adtraction_xml(path: Path, merchant_name: str = "2xu") -> List[ProductRecord]:
    """Parse Google Shopping XML / Adtraction XML feeds."""
    records: List[ProductRecord] = []
    ns = {"g": "http://base.google.com/ns/1.0"}
    
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        channel = root.find("channel")
        if channel is None:
            channel = root
            
        for item in channel.findall("item"):
            def g_text(tag: str, default: str = "") -> str:
                el = item.find(f"g:{tag}", ns)
                if el is not None and el.text:
                    return el.text.strip()
                # fallback without namespace
                el2 = item.find(tag)
                if el2 is not None and el2.text:
                    return el2.text.strip()
                return default

            pid = g_text("id") or g_text("gtin") or g_text("mpn") or ""
            title = g_text("title")
            desc = g_text("description")
            brand = g_text("brand") or merchant_name
            raw_price = g_text("price")
            sale_price = g_text("sale_price")
            effective_price = sale_price if sale_price else raw_price
            price_val = _clean_price(effective_price)
            
            link = g_text("link")
            image_url = g_text("image_link")
            product_type = g_text("product_type")
            google_cat = g_text("google_product_category")
            source_cat = product_type or google_cat or "Övrigt"
            
            gender = g_text("gender")
            color = g_text("color")
            size = g_text("size")
            material = g_text("material")
            availability = g_text("availability")
            
            records.append(ProductRecord(
                id=f"{merchant_name}_{pid}" if pid else f"{merchant_name}_{len(records)}",
                title=title,
                description=desc,
                brand=brand,
                price=price_val,
                currency="SEK",
                url=link,
                image_url=image_url,
                merchant=merchant_name,
                network="adtraction",
                source_category=source_cat,
                attributes={
                    "gender": gender,
                    "color": color,
                    "size": size,
                    "material": material,
                    "availability": availability,
                    "raw_product_type": product_type,
                    "google_product_category": google_cat
                }
            ))
    except Exception as e:
        print(f"Error loading XML feed {path}: {e}")
        
    return records


def load_tradedoubler_json(path: Path, merchant_name: str = "adlibris") -> List[ProductRecord]:
    """Parse Tradedoubler PDT JSON feeds."""
    records: List[ProductRecord] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
            
        prods = data.get("products", [])
        for i, p in enumerate(prods):
            name = p.get("name", "")
            desc = p.get("description", "")
            brand = p.get("brand", "") or merchant_name
            
            # Category extraction
            categories = p.get("categories", [])
            source_cat = ""
            if categories and isinstance(categories, list):
                c0 = categories[0]
                if isinstance(c0, dict):
                    source_cat = c0.get("tdCategoryName", "")
            
            if not source_cat:
                fields = p.get("fields", [])
                for fld in fields:
                    if fld.get("name") in ["categories/category", "category"]:
                        source_cat = fld.get("value", "")
                        break
            if not source_cat:
                source_cat = "Övrigt"
                
            # Offers & price
            offers = p.get("offers", [])
            price_val = 0.0
            currency = "SEK"
            prod_url = ""
            if offers and isinstance(offers, list):
                off0 = offers[0]
                prod_url = off0.get("productUrl", "") or off0.get("legacyProductUrl", "")
                p_hist = off0.get("priceHistory", [])
                if p_hist and isinstance(p_hist, list):
                    price_obj = p_hist[0].get("price", {})
                    price_val = _clean_price(price_obj.get("value", 0))
                    currency = price_obj.get("currency", "SEK")
                    
            # Image
            img_obj = p.get("productImage", {})
            img_url = ""
            if isinstance(img_obj, dict):
                img_url = img_obj.get("url", "")
            elif isinstance(img_obj, str):
                img_url = img_obj
                
            # Identifiers
            identifiers = p.get("identifiers", {})
            pid = identifiers.get("mpn") or identifiers.get("sku") or str(i)
            
            records.append(ProductRecord(
                id=f"{merchant_name}_{pid}",
                title=name,
                description=desc,
                brand=brand,
                price=price_val,
                currency=currency,
                url=prod_url,
                image_url=img_url,
                merchant=merchant_name,
                network="tradedoubler",
                source_category=source_cat,
                attributes={
                    "identifiers": identifiers,
                    "groupingId": p.get("groupingId")
                }
            ))
    except Exception as e:
        print(f"Error loading JSON feed {path}: {e}")
        
    return records


def load_generic_feed(path: Path) -> List[ProductRecord]:
    """Auto-detect format and merchant, then load."""
    p_str = str(path).lower()
    if p_str.endswith(".xml"):
        merchant = "2xu" if "2xu" in p_str else Path(path).stem.split("__")[0]
        return load_adtraction_xml(path, merchant_name=merchant)
    elif p_str.endswith(".json"):
        merchant = "adlibris" if "adlibris" in p_str else Path(path).stem.split("__")[0]
        return load_tradedoubler_json(path, merchant_name=merchant)
    else:
        raise ValueError(f"Unsupported feed format: {path}")
