import torch
from typing import List, Dict, Tuple
from .schemas import LogEvent

class GraphBuilder:
    """
    Converts a batch of LogEvents into a Graph structure (Nodes, Edges).
    Maintains a mapping of Entity ID -> Node Index.
    """
    def __init__(self, feature_dim: int = 16):
        self.node_map: Dict[str, int] = {}  # Entity ID -> Index
        self.feature_dim = feature_dim
        
    def _get_or_create_node(self, entity_id: str) -> int:
        if entity_id not in self.node_map:
            self.node_map[entity_id] = len(self.node_map)
        return self.node_map[entity_id]

    def build_graph(self, events: List[LogEvent]):
        """
        Returns:
            x (Tensor): Node features [Num_Nodes, Feature_Dim]
            edge_index (Tensor): Connectivity [2, Num_Edges]
            edge_mapping (List[str]): Map from edge_index col to event_id
        """
        src_indices = []
        dst_indices = []
        edge_event_ids = []
        
        # 1. Parse events to build topology
        for event in events:
            u = self._get_or_create_node(event.source_entity)
            v = self._get_or_create_node(event.destination_entity)
            
            src_indices.append(u)
            dst_indices.append(v)
            edge_event_ids.append(event.event_id)
            
        edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
        
        # 2. Generate Semantic Node Features
        # Categorize entities and assign meaningful base features
        num_nodes = len(self.node_map)
        x = torch.zeros((num_nodes, self.feature_dim))
        
        # Define semantic categories and their base characteristics
        # In a real app, these would be learnable or domain-driven
        category_bases = {
            "user": torch.ones(self.feature_dim) * 0.5,
            "patient": torch.ones(self.feature_dim) * -0.5,
            "ip": torch.tensor([1.0 if i % 2 == 0 else -1.0 for i in range(self.feature_dim)]),
            "system": torch.zeros(self.feature_dim),
            "unknown": torch.randn(self.feature_dim) * 0.1
        }
        
        for entity_id, idx in self.node_map.items():
            # Identity type based on prefix
            category = "unknown"
            if entity_id.startswith("user_"): category = "user"
            elif entity_id.startswith("patient_"): category = "patient"
            elif entity_id.startswith("ip_"): category = "ip"
            elif entity_id.startswith("system_"): category = "system"
            
            base = category_bases[category]
            
            # Combine base with deterministic noise for uniqueness
            torch.manual_seed(hash(entity_id) % (2**32))
            noise = torch.randn(self.feature_dim) * 0.1
            x[idx] = base + noise
            
        return x, edge_index, edge_event_ids
