
import unittest
import torch
from backend.anomaly_detector.models.gnn_baseline import EdgeLevelGNN
from backend.anomaly_detector.models.prototype_gnn import PrototypeGNN
from backend.anomaly_detector.models.contrastive_gnn import ContrastiveGNN, SupervisedContrastiveLoss
from backend.anomaly_detector.models.gsl_gnn import GSLGNN


class TestBaseModel:
    """Base test class with common setup for all GNN tests."""
    input_dim = 16
    hidden_dim = 32
    
    def get_mock_data(self, num_nodes=5):
        """Create mock graph data for testing."""
        x = torch.randn(num_nodes, self.input_dim)
        # Simple chain graph
        edge_index = torch.tensor([
            [0, 1, 1, 2, 2, 3, 3, 4],
            [1, 0, 2, 1, 3, 2, 4, 3]
        ], dtype=torch.long)
        return x, edge_index


class TestEdgeLevelGNN(unittest.TestCase, TestBaseModel):
    """Tests for the baseline EdgeLevelGNN model."""
    
    def setUp(self):
        self.model = EdgeLevelGNN(self.input_dim, self.hidden_dim)
        self.model.eval()

    def test_model_structure(self):
        """Verify layer dimensions."""
        self.assertEqual(self.model.conv1.lin.in_features, self.input_dim)
        self.assertEqual(self.model.conv1.lin.out_features, self.hidden_dim)
        self.assertEqual(self.model.conv2.lin.in_features, self.hidden_dim)
        
    def test_forward_pass(self):
        """Verify forward pass produces valid probabilities."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            scores = self.model(x, edge_index)
            
        # Output should be one score per edge
        self.assertEqual(scores.shape[0], edge_index.shape[1])
        # Scores should be probabilities [0, 1]
        self.assertTrue(torch.all(scores >= 0.0))
        self.assertTrue(torch.all(scores <= 1.0))


class TestPrototypeGNN(unittest.TestCase, TestBaseModel):
    """Tests for the Prototype-GNN model (94.24% accuracy)."""
    
    def setUp(self):
        self.num_prototypes = 3
        self.model = PrototypeGNN(
            node_input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            num_classes=2,
            num_prototypes_per_class=self.num_prototypes,
            temperature=0.1
        )
        self.model.eval()

    def test_prototype_parameters(self):
        """Verify prototype parameters are correctly initialized."""
        # Prototypes should have shape [num_classes, num_prototypes, hidden_dim]
        self.assertEqual(self.model.prototypes.shape, (2, self.num_prototypes, self.hidden_dim))
        
    def test_forward_pass(self):
        """Verify forward pass produces valid probabilities."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            scores = self.model(x, edge_index)
            
        # Output should be one score per edge
        self.assertEqual(scores.shape[0], edge_index.shape[1])
        # Scores should be probabilities [0, 1]
        self.assertTrue(torch.all(scores >= 0.0))
        self.assertTrue(torch.all(scores <= 1.0))
        
    def test_prototype_distances(self):
        """Verify prototype distance computation."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            node_embeddings = self.model.encode_nodes(x, edge_index)
            edge_embeddings = self.model.get_edge_embeddings(node_embeddings, edge_index)
            logits = self.model.compute_prototype_distances(edge_embeddings)
            
        # Logits should have shape [num_edges, num_classes]
        self.assertEqual(logits.shape, (edge_index.shape[1], 2))


class TestContrastiveGNN(unittest.TestCase, TestBaseModel):
    """Tests for the Contrastive-GNN model (94.71% accuracy)."""
    
    def setUp(self):
        self.projection_dim = 64
        self.model = ContrastiveGNN(
            node_input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            projection_dim=self.projection_dim,
            num_classes=2
        )
        self.model.eval()

    def test_forward_pass(self):
        """Verify forward pass produces valid probabilities."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            scores = self.model(x, edge_index)
            
        # Output should be one score per edge
        self.assertEqual(scores.shape[0], edge_index.shape[1])
        # Scores should be probabilities [0, 1]
        self.assertTrue(torch.all(scores >= 0.0))
        self.assertTrue(torch.all(scores <= 1.0))
        
    def test_forward_with_projections(self):
        """Verify forward pass returns projections when requested."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            scores, projections = self.model(x, edge_index, return_projections=True)
            
        # Projections should have shape [num_edges, projection_dim]
        self.assertEqual(projections.shape, (edge_index.shape[1], self.projection_dim))
        # Projections should be L2-normalized (magnitude ~1)
        norms = torch.norm(projections, dim=1)
        self.assertTrue(torch.allclose(norms, torch.ones_like(norms), atol=1e-5))
        
    def test_contrastive_loss(self):
        """Verify supervised contrastive loss computation."""
        loss_fn = SupervisedContrastiveLoss(temperature=0.07)
        
        # Mock projections and labels
        projections = torch.randn(8, self.projection_dim)
        projections = torch.nn.functional.normalize(projections, dim=1)
        labels = torch.tensor([0, 0, 0, 0, 1, 1, 1, 1])
        
        loss = loss_fn(projections, labels)
        
        # Loss should be a scalar
        self.assertEqual(loss.shape, ())
        # Loss should be non-negative
        self.assertGreaterEqual(loss.item(), 0.0)


class TestGSLGNN(unittest.TestCase, TestBaseModel):
    """Tests for the GSL-GNN model (96.66% accuracy) - BEST PERFORMING."""
    
    def setUp(self):
        self.gsl_hidden_dim = 32
        self.model = GSLGNN(
            node_input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            num_classes=2,
            gsl_hidden_dim=self.gsl_hidden_dim
        )
        self.model.eval()

    def test_forward_pass(self):
        """Verify forward pass produces valid probabilities."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            scores = self.model(x, edge_index)
            
        # Output should be one score per edge
        self.assertEqual(scores.shape[0], edge_index.shape[1])
        # Scores should be probabilities [0, 1]
        self.assertTrue(torch.all(scores >= 0.0))
        self.assertTrue(torch.all(scores <= 1.0))
        
    def test_learned_graph_structure(self):
        """Verify graph structure learning produces valid adjacency."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            learned_adj = self.model.get_learned_graph(x, edge_index)
            
        num_nodes = x.shape[0]
        # Learned adjacency should be [num_nodes, num_nodes]
        self.assertEqual(learned_adj.shape, (num_nodes, num_nodes))
        # Values should be in [0, 1] range (after sigmoid)
        self.assertTrue(torch.all(learned_adj >= 0.0))
        self.assertTrue(torch.all(learned_adj <= 1.0))
        
    def test_dual_branch_encoding(self):
        """Verify both graph branches produce embeddings."""
        x, edge_index = self.get_mock_data()
        
        with torch.no_grad():
            # Get learned adjacency
            learned_adj = self.model.gsl(x, edge_index)
            learned_adj = learned_adj + torch.eye(x.shape[0])
            degree = learned_adj.sum(dim=1, keepdim=True).clamp(min=1)
            learned_adj = learned_adj / degree
            
            # Test both encoding branches
            h_learned = self.model.encode_with_learned_graph(x, learned_adj)
            h_original = self.model.encode_with_original_graph(x, edge_index)
            
        # Both should produce [num_nodes, hidden_dim] embeddings
        self.assertEqual(h_learned.shape, (x.shape[0], self.hidden_dim))
        self.assertEqual(h_original.shape, (x.shape[0], self.hidden_dim))


if __name__ == '__main__':
    unittest.main()
