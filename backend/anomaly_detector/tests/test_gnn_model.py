
import unittest
import torch
from backend.anomaly_detector.models.gnn_baseline import EdgeLevelGNN

class TestGNNModel(unittest.TestCase):
    def setUp(self):
        self.input_dim = 16
        self.hidden_dim = 32
        self.model = EdgeLevelGNN(self.input_dim, self.hidden_dim)
        self.model.eval()

    def test_model_structure(self):
        """Verify layer dimensions."""
        self.assertEqual(self.model.conv1.lin.in_features, self.input_dim)
        self.assertEqual(self.model.conv1.lin.out_features, self.hidden_dim)
        self.assertEqual(self.model.conv2.lin.in_features, self.hidden_dim)
        
    def test_forward_pass(self):
        """Verify forward pass logic matches PyG expectations."""
        # 1. Mock Data
        num_nodes = 5
        x = torch.randn(num_nodes, self.input_dim)
        
        # fully connected edge index
        edge_index = torch.tensor([
            [0, 1, 1, 2, 2, 3, 3, 4],
            [1, 0, 2, 1, 3, 2, 4, 3]
        ], dtype=torch.long)
        
        # 2. Inference
        with torch.no_grad():
            scores = self.model(x, edge_index)
            
        # 3. Assertions
        # Output should be one score per edge
        self.assertEqual(scores.shape[0], edge_index.shape[1])
        # Scores should be probabilities [0, 1]
        self.assertTrue(torch.all(scores >= 0.0))
        self.assertTrue(torch.all(scores <= 1.0))

if __name__ == '__main__':
    unittest.main()
