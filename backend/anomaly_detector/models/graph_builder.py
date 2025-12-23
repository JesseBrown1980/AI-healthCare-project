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
        
        # 2. Generate Dummy Node Features (in real app, use one-hot or semantic features)
        # Simply random or constant for baseline
        num_nodes = len(self.node_map)
        # Using random features for now as placeholder
        x = torch.randn((num_nodes, self.feature_dim))
        
        return x, edge_index, edge_event_ids
