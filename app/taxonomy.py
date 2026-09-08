"""
Taxonomy manager for raizemore.com.
Maintains and validates the standardized master category tree (max depth 4).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class CategoryNode:
    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.level: int = data.get("level", 1)
        self.parent_id: Optional[str] = data.get("parent_id")
        self.keywords: List[str] = data.get("keywords", [])
        self.children: List["CategoryNode"] = []
        self.product_count: int = 0
        
        raw_children = data.get("children", [])
        for ch in raw_children:
            self.children.append(CategoryNode(ch))

    def to_dict(self, include_counts: bool = True) -> Dict[str, Any]:
        res = {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "parent_id": self.parent_id,
            "keywords": self.keywords,
            "children": [ch.to_dict(include_counts) for ch in self.children]
        }
        if include_counts:
            res["product_count"] = self.product_count
        return res


class Taxonomy:
    def __init__(self, json_path: Optional[Path] = None):
        if json_path is None:
            json_path = Path(__file__).parent / "rules" / "master_taxonomy.json"
        
        self.json_path = Path(json_path)
        self.root_nodes: List[CategoryNode] = []
        self._index: Dict[str, CategoryNode] = {}
        self.max_depth: int = 4
        self.load()

    def load(self):
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.max_depth = data.get("max_depth", 4)
        self.root_nodes = [CategoryNode(c) for c in data.get("categories", [])]
        self._index.clear()
        self._build_index(self.root_nodes)
        self.validate()

    def _build_index(self, nodes: List[CategoryNode]):
        for node in nodes:
            self._index[node.id] = node
            if node.children:
                self._build_index(node.children)

    def validate(self):
        """Ensure no node exceeds max_depth, IDs are unique, and parents exist."""
        for cid, node in self._index.items():
            if node.level > self.max_depth:
                raise ValueError(f"Category {cid} exceeds max allowed depth ({self.max_depth}): level={node.level}")
            if node.parent_id and node.parent_id not in self._index:
                raise ValueError(f"Category {cid} has non-existent parent {node.parent_id}")

    def get(self, category_id: str) -> Optional[CategoryNode]:
        return self._index.get(category_id)

    def all_categories(self) -> List[CategoryNode]:
        return list(self._index.values())

    def get_breadcrumb(self, category_id: str) -> List[Dict[str, Any]]:
        trail = []
        curr = self.get(category_id)
        while curr:
            trail.append({"id": curr.id, "name": curr.name, "level": curr.level})
            if not curr.parent_id:
                break
            curr = self.get(curr.parent_id)
        trail.reverse()
        return trail

    def get_path_string(self, category_id: str) -> str:
        crumb = self.get_breadcrumb(category_id)
        return " > ".join(c["name"] for c in crumb)

    def reset_counts(self):
        for node in self._index.values():
            node.product_count = 0

    def increment_count(self, category_id: str):
        curr = self.get(category_id)
        while curr:
            curr.product_count += 1
            if not curr.parent_id:
                break
            curr = self.get(curr.parent_id)

    def to_tree_dict(self) -> List[Dict[str, Any]]:
        return [node.to_dict(include_counts=True) for node in self.root_nodes]
