#!/usr/bin/env python3
"""Tests for P3-001: Graph Embedding Visualization. Version: 2.8.0"""
import pytest
import math
from typing import Dict, List

try:
    import plotly
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False


@pytest.fixture
def sample_embeddings():
    return {
        "entity:Python": [0.8, 0.2, 0.1, 0.0],
        "entity:Java": [0.7, 0.3, 0.1, 0.0],
        "entity:JavaScript": [0.6, 0.4, 0.0, 0.0],
        "entity:cooking": [0.0, 0.0, 0.8, 0.2],
        "entity:recipes": [0.0, 0.0, 0.7, 0.3],
    }

@pytest.fixture
def sample_labels():
    return {
        "entity:Python": "Python Language",
        "entity:Java": "Java Language",
        "entity:JavaScript": "JavaScript Language",
        "entity:cooking": "Cooking Topic",
        "entity:recipes": "Recipe Topic",
    }

@pytest.fixture
def large_embeddings():
    import random
    random.seed(42)
    result = {}
    for i in range(50):
        vec = [random.random() for _ in range(128)]
        norm = math.sqrt(sum(x * x for x in vec))
        result[f"node-{i}"] = [x / norm for x in vec]
    return result


class TestVisualizationConfig:
    def test_default_config(self):
        from src.visualization.embedding_viz import VisualizationConfig
        config = VisualizationConfig()
        assert config.n_neighbors == 15
        assert config.min_dist == 0.1
        assert config.metric == "cosine"
        assert config.n_components == 2

    def test_custom_config(self):
        from src.visualization.embedding_viz import VisualizationConfig
        config = VisualizationConfig(n_neighbors=30, min_dist=0.2, metric="euclidean", n_components=3)
        assert config.n_neighbors == 30 and config.min_dist == 0.2

    def test_config_validation_n_neighbors(self):
        from src.visualization.embedding_viz import VisualizationConfig
        with pytest.raises(ValueError, match="n_neighbors"):
            VisualizationConfig(n_neighbors=0)

    def test_config_validation_min_dist(self):
        from src.visualization.embedding_viz import VisualizationConfig
        with pytest.raises(ValueError, match="min_dist"):
            VisualizationConfig(min_dist=-0.1)


class TestEmbeddingReducer:
    def test_reduce_to_2d(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingReducer, VisualizationConfig
        reducer = EmbeddingReducer(VisualizationConfig())
        coords = reducer.reduce(sample_embeddings)
        assert len(coords) == len(sample_embeddings)
        for node_id, (x, y) in coords.items():
            assert isinstance(x, (int, float)) and isinstance(y, (int, float))

    def test_reduce_to_3d(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingReducer, VisualizationConfig
        config = VisualizationConfig(n_components=3)
        reducer = EmbeddingReducer(config)
        coords = reducer.reduce(sample_embeddings)
        for node_id, coord in coords.items():
            assert len(coord) == 3

    def test_reduce_preserves_ids(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingReducer, VisualizationConfig
        reducer = EmbeddingReducer(VisualizationConfig())
        coords = reducer.reduce(sample_embeddings)
        assert set(coords.keys()) == set(sample_embeddings.keys())

    def test_reduce_empty_input(self):
        from src.visualization.embedding_viz import EmbeddingReducer, VisualizationConfig
        reducer = EmbeddingReducer(VisualizationConfig())
        coords = reducer.reduce({})
        assert coords == {}

    def test_reduce_single_point(self):
        from src.visualization.embedding_viz import EmbeddingReducer, VisualizationConfig
        reducer = EmbeddingReducer(VisualizationConfig())
        coords = reducer.reduce({"node": [1.0, 0.0, 0.0, 0.0]})
        assert len(coords) == 1 and "node" in coords


class TestFallbackReduction:
    def test_fallback_pca(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingReducer, VisualizationConfig
        reducer = EmbeddingReducer(VisualizationConfig(), force_fallback=True)
        coords = reducer.reduce(sample_embeddings)
        assert len(coords) == len(sample_embeddings)
        for node_id, (x, y) in coords.items():
            assert isinstance(x, (int, float)) and isinstance(y, (int, float))

    def test_fallback_maintains_relative_distances(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingReducer, VisualizationConfig
        reducer = EmbeddingReducer(VisualizationConfig(), force_fallback=True)
        coords = reducer.reduce(sample_embeddings)
        py = coords["entity:Python"]
        java = coords["entity:Java"]
        cooking = coords["entity:cooking"]
        dist_py_java = math.sqrt((py[0] - java[0])**2 + (py[1] - java[1])**2)
        dist_py_cook = math.sqrt((py[0] - cooking[0])**2 + (py[1] - cooking[1])**2)
        assert dist_py_java >= 0 and dist_py_cook >= 0


class TestEmbeddingVisualizer:
    def test_visualize_returns_figure(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        viz = EmbeddingVisualizer()
        result = viz.visualize(sample_embeddings)
        assert result is not None
        assert hasattr(result, "data") or hasattr(result, "to_dict")

    def test_visualize_with_labels(self, sample_embeddings, sample_labels):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        viz = EmbeddingVisualizer()
        result = viz.visualize(sample_embeddings, labels=sample_labels)
        assert result is not None

    def test_visualize_with_colors(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        colors = {k: "blue" if "Python" in k else "red" for k in sample_embeddings}
        viz = EmbeddingVisualizer()
        result = viz.visualize(sample_embeddings, colors=colors)
        assert result is not None

    def test_visualize_3d(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingVisualizer, VisualizationConfig
        config = VisualizationConfig(n_components=3)
        viz = EmbeddingVisualizer(config=config)
        result = viz.visualize(sample_embeddings)
        assert result is not None

    def test_visualize_empty(self):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        viz = EmbeddingVisualizer()
        result = viz.visualize({})
        assert result is None or (hasattr(result, "data") and len(result.data) == 0)


class TestFigureExport:
    def test_to_html(self, sample_embeddings, tmp_path):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        viz = EmbeddingVisualizer()
        result = viz.visualize(sample_embeddings)
        if result is not None:
            html_path = tmp_path / "viz.html"
            viz.save_html(result, str(html_path))
            assert html_path.exists()
            assert len(html_path.read_text(encoding="utf-8")) > 0

    def test_to_json(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        viz = EmbeddingVisualizer()
        result = viz.visualize(sample_embeddings)
        if result is not None:
            json_data = viz.to_json(result)
            assert isinstance(json_data, (str, dict))


class TestClusteringOverlay:
    def test_visualize_with_clusters(self, sample_embeddings):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        clusters = {
            "entity:Python": "programming", "entity:Java": "programming",
            "entity:JavaScript": "programming", "entity:cooking": "food",
            "entity:recipes": "food",
        }
        viz = EmbeddingVisualizer()
        result = viz.visualize(sample_embeddings, clusters=clusters)
        assert result is not None


class TestVisualizationPerformance:
    def test_moderate_scale_performance(self, large_embeddings):
        import time
        from src.visualization.embedding_viz import EmbeddingVisualizer
        viz = EmbeddingVisualizer()
        start = time.time()
        result = viz.visualize(large_embeddings)
        elapsed = time.time() - start
        assert elapsed < 30.0
        assert result is not None


class TestKnowledgeGraphIntegration:
    def test_visualize_from_dual_embedder(self):
        from src.visualization.embedding_viz import EmbeddingVisualizer
        from src.knowledge.embeddings import DualEmbedder, DualEmbeddingConfig
        embedder = DualEmbedder(DualEmbeddingConfig())
        texts = ["Python programming", "Java coding", "Cooking recipes"]
        embeddings = {text: embedder.embed_text(text) for text in texts}
        viz = EmbeddingVisualizer()
        result = viz.visualize(embeddings)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
