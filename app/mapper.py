"""
Core Categorization & Mapping Engine for raizemore.com.
Provides hierarchical 3-tier mapping:
  1. Direct Merchant/Network Category Rules
  2. Attribute Refinement (Gender, Type)
  3. Automated Zero-Touch Semantic Matcher (for unseen feeds 3-200)
  4. Title/Keyword Heuristics
  5. Guaranteed Fallback (100% Categorization Guarantee)
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from app.taxonomy import Taxonomy, CategoryNode
from app.feed_loaders import ProductRecord


SWEDISH_STOPWORDS = {"och", "eller", "for", "för", "i", "med", "av", "pa", "på", "till", "ett", "en"}
SWEDISH_SUFFIXES = ["erna", "arna", "orna", "ande", "else", "het", "ens", "ars", "ers", "en", "et", "na", "ar", "er", "or", "at", "a"]


def _stem(word: str) -> str:
    """Simple Swedish stemmer for suffixes."""
    w = word.lower()
    for suff in SWEDISH_SUFFIXES:
        if len(w) > len(suff) + 3 and w.endswith(suff):
            return w[:-len(suff)]
    return w


def _normalize_text(text: str) -> str:
    """Normalize text: lowercase, remove punctuation, strip whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = text.replace("å", "a").replace("ä", "a").replace("ö", "o")
    text = re.sub(r"[>/\-_&+,:;()'\"]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_ngrams(text: str, n: int = 3) -> set:
    """Character n-grams for fuzzy compound word matching."""
    s = f" {text} "
    return set(s[i:i+n] for i in range(len(s) - n + 1))


def _similarity(s1: str, s2: str) -> float:
    """Compute token Jaccard + n-gram similarity between two strings."""
    norm1 = _normalize_text(s1)
    norm2 = _normalize_text(s2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
        
    raw_tokens1 = [t for t in norm1.split() if t not in SWEDISH_STOPWORDS]
    raw_tokens2 = [t for t in norm2.split() if t not in SWEDISH_STOPWORDS]
    
    stem_tokens1 = set(_stem(t) for t in raw_tokens1)
    stem_tokens2 = set(_stem(t) for t in raw_tokens2)
    
    # Exact stem token overlap
    intersection = stem_tokens1.intersection(stem_tokens2)
    union = stem_tokens1.union(stem_tokens2)
    token_score = len(intersection) / len(union) if union else 0.0
    
    # Substring containment bonus
    for t1 in stem_tokens1:
        for t2 in stem_tokens2:
            if len(t1) >= 4 and len(t2) >= 4 and (t1 in t2 or t2 in t1):
                token_score = max(token_score, 0.70)
                
    # Character 3-grams for compound word detection
    ng1 = _get_ngrams(norm1, 3)
    ng2 = _get_ngrams(norm2, 3)
    ng_union = ng1.union(ng2)
    ngram_score = len(ng1.intersection(ng2)) / len(ng_union) if ng_union else 0.0
    
    return 0.65 * token_score + 0.35 * ngram_score


class CategoryMapper:
    def __init__(self, taxonomy: Taxonomy, rules_dir: Optional[Path] = None):
        self.taxonomy = taxonomy
        if rules_dir is None:
            rules_dir = Path(__file__).parent / "rules"
            
        self.rules_dir = Path(rules_dir)
        self.exact_mappings: Dict[Tuple[str, str], str] = {} # (merchant, source_cat) -> target_id
        self.network_mappings: Dict[Tuple[str, str], str] = {} # (network, source_cat) -> target_id
        self.attribute_rules: List[Dict[str, Any]] = []
        self.mapping_cache: Dict[str, Tuple[str, str, float]] = {} # source_cat -> (target_id, rule_name, conf)
        
        self.load_rules()

    def load_rules(self):
        # Load category mappings
        cat_file = self.rules_dir / "category_mappings.json"
        if cat_file.exists():
            with open(cat_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for m in data.get("mappings", []):
                    target_id = m.get("target_category_id")
                    if not self.taxonomy.get(target_id):
                        continue
                    sc = m.get("source_category", "").strip().lower()
                    merchant = m.get("merchant", "").strip().lower()
                    network = m.get("network", "").strip().lower()
                    if merchant:
                        self.exact_mappings[(merchant, sc)] = (target_id, m.get("rule_name", "Direct Rule"))
                    elif network:
                        self.network_mappings[(network, sc)] = (target_id, m.get("rule_name", "Network Rule"))

        # Load attribute rules
        attr_file = self.rules_dir / "attribute_rules.json"
        if attr_file.exists():
            with open(attr_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.attribute_rules = data.get("attribute_rules", [])

    def map_product(self, p: ProductRecord) -> ProductRecord:
        """Map a single product into the master taxonomy."""
        cat_id, rule_name, confidence = self.resolve_category(
            source_cat=p.source_category,
            title=p.title,
            brand=p.brand,
            merchant=p.merchant,
            network=p.network,
            attributes=p.attributes
        )
        
        p.category_id = cat_id
        p.category_path = self.taxonomy.get_path_string(cat_id)
        p.mapping_rule = rule_name
        p.mapping_confidence = round(confidence, 2)
        
        # Update product count in taxonomy
        self.taxonomy.increment_count(cat_id)
        return p

    def map_batch(self, products: List[ProductRecord]) -> List[ProductRecord]:
        """Map a batch of products with maximum throughput."""
        for p in products:
            self.map_product(p)
        return products

    def resolve_category(
        self, 
        source_cat: str, 
        title: str = "", 
        brand: str = "",
        merchant: str = "", 
        network: str = "", 
        attributes: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, float]:
        """
        Hierarchical resolution pipeline:
          1. Attribute-specific rule matching (e.g. gender split)
          2. Exact merchant/network category mapping
          3. Fast cache lookup
          4. Zero-touch semantic similarity matching against master taxonomy
          5. Keyword title search
          6. Guaranteed domain fallback
        """
        if attributes is None:
            attributes = {}
            
        norm_sc = (source_cat or "").strip().lower()
        norm_merchant = (merchant or "").strip().lower()
        norm_network = (network or "").strip().lower()
        
        # --- Tier 1: Attribute-Aware Rules (Gender, Apparel splits) ---
        gender = attributes.get("gender", "")
        # If gender not in attributes, check title for Dam / Herr / Women / Men
        if not gender and title:
            t_low = title.lower()
            if "dam" in t_low or "women" in t_low or "kvinna" in t_low:
                gender = "Dam"
            elif "herr" in t_low or "men" in t_low or "man " in t_low:
                gender = "Herr"

        for arule in self.attribute_rules:
            patterns = arule.get("source_patterns", [])
            for pat in patterns:
                if pat.lower() in norm_sc or pat.lower() == norm_sc:
                    routes = arule.get("routes", {})
                    target_id = routes.get(gender) or routes.get("default")
                    if target_id and self.taxonomy.get(target_id):
                        return (target_id, f"Attribute Rule [{pat} + {gender or 'Default'}]", 0.98)

        # --- Tier 2: Exact Merchant Category Rule ---
        if (norm_merchant, norm_sc) in self.exact_mappings:
            target_id, rule_name = self.exact_mappings[(norm_merchant, norm_sc)]
            # Refine with title if it's broad (e.g., Adlibris Utomhusaktiviteter)
            if "kubb-kastspel" in target_id and title:
                t_lower = title.lower()
                if "boule" in t_lower or "boccia" in t_lower:
                    target_id = "leksaker-spel/utomhuslek/klassiska-utespel/boule-boccia"
                    rule_name = "Adlibris Utespel (Boule/Boccia Title Match)"
            return (target_id, f"Direct Rule: {rule_name}", 1.0)

        # --- Tier 2b: Network-Level Category Rule ---
        if (norm_network, norm_sc) in self.network_mappings:
            target_id, rule_name = self.network_mappings[(norm_network, norm_sc)]
            return (target_id, f"Network Rule: {rule_name}", 0.95)

        # --- Tier 3: Zero-Touch Semantic Matcher (For unknown categories from feeds 3-200) ---
        best_match, best_score = self._semantic_match(source_cat)
        if best_match and best_score >= 0.35:
            # If best_match has children and title is provided, check if title refines to a child leaf
            if best_match.children and title:
                child_match, child_score = self._semantic_match(f"{source_cat} {title}")
                if child_match and child_match.level > best_match.level:
                    return (child_match.id, f"Auto-Matcher + Titelförfining ({int(child_score*100)}%)", child_score)
            return (best_match.id, f"Auto-Matcher ({int(best_score*100)}% likhet)", best_score)

        # --- Tier 4: Title / Keyword Heuristic ---
        if title:
            title_match, title_score = self._semantic_match(title)
            if title_match and title_score >= 0.45:
                return (title_match.id, f"Titel-heuristik ({int(title_score*100)}% likhet)", title_score)

        # --- Tier 5: Guaranteed Fallback (No product left behind) ---
        # Domain heuristic based on merchant or brand
        if any(w in norm_merchant for w in ["sport", "2xu", "stadium", "running", "gym"]):
            return ("sport-traning/sportutrustning-tillbehor/ovrigt/allmant", "Fallback: Sport & Träning", 0.50)
        elif any(w in norm_merchant for w in ["bok", "libris", "spel", "leksak", "toy"]):
            return ("leksaker-spel/sallskapsspel/ovriga-spel/allmant", "Fallback: Leksaker & Spel", 0.50)
        else:
            return ("sport-traning/sportutrustning-tillbehor/ovrigt/allmant", "Global Fallback", 0.30)

    def _semantic_match(self, query: str) -> Tuple[Optional[CategoryNode], float]:
        """
        Find the best matching category node using Informational Token Coverage & Specificity.
        Prioritizes nodes that cover the highest number of query tokens, breaking ties in favor
        of deeper, more specific leaf nodes.
        """
        if not query:
            return (None, 0.0)
            
        norm_q = _normalize_text(query)
        q_tokens = set(_stem(t) for t in norm_q.split() if t not in SWEDISH_STOPWORDS)
        if not q_tokens:
            return (None, 0.0)
            
        best_node: Optional[CategoryNode] = None
        best_rank: Tuple[int, int, float] = (0, 0, 0.0)
        
        all_nodes = self.taxonomy.all_categories()
        for node in all_nodes:
            path_str = self.taxonomy.get_path_string(node.id)
            vocab_text = f"{path_str} {' '.join(node.keywords)}"
            v_norm = _normalize_text(vocab_text)
            v_tokens = set(_stem(t) for t in v_norm.split() if t not in SWEDISH_STOPWORDS)
            
            inter = q_tokens.intersection(v_tokens)
            if not inter:
                continue
                
            inter_count = len(inter)
            name_sim = _similarity(query, node.name)
            
            # Rank tuple: (number of matched query tokens, hierarchy depth, string similarity)
            current_rank = (inter_count, node.level, name_sim)
            if current_rank > best_rank:
                best_rank = current_rank
                best_node = node
                
        if not best_node:
            return (None, 0.0)
            
        # Confidence based on token coverage & depth
        coverage = best_rank[0] / len(q_tokens)
        confidence = min(round(coverage * 0.85 + (best_node.level * 0.03), 2), 0.99)
        return (best_node, confidence)

    def simulate_match(
        self, 
        source_category: str, 
        title: str = "", 
        merchant: str = "Testbutik", 
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Diagnostic simulator to show how any input from any feed is processed."""
        cat_id, rule_name, conf = self.resolve_category(
            source_cat=source_category,
            title=title,
            merchant=merchant,
            attributes=attributes or {}
        )
        node = self.taxonomy.get(cat_id)
        breadcrumb = self.taxonomy.get_breadcrumb(cat_id) if node else []
        
        # Also find top 3 candidate alternatives for comparison
        candidates = []
        for n in self.taxonomy.all_categories():
            if n.level in [3, 4]:
                sim = _similarity(f"{source_category} {title}", f"{n.name} {' '.join(n.keywords)}")
                candidates.append({
                    "id": n.id,
                    "name": n.name,
                    "level": n.level,
                    "path": self.taxonomy.get_path_string(n.id),
                    "score": round(sim, 2)
                })
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "input": {
                "source_category": source_category,
                "title": title,
                "merchant": merchant,
                "attributes": attributes or {}
            },
            "result": {
                "target_category_id": cat_id,
                "target_category_name": node.name if node else "Okänd",
                "target_category_level": node.level if node else 0,
                "breadcrumb": breadcrumb,
                "path_string": self.taxonomy.get_path_string(cat_id) if node else "",
                "rule_applied": rule_name,
                "confidence": round(conf, 2),
                "top_candidates": candidates[:3]
            }
        }
