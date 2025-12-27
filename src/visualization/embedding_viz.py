"""
Graph Embedding Visualization for Knowledge Graph.

Provides interactive 2D/3D visualization of embeddings using UMAP
dimensionality reduction and Plotly for rendering.

P3-001: Graph Embedding Visualization
- UMAP/PCA dimensionality reduction
- Interactive Plotly scatter plots
- Cluster overlay support
- Fallback when dependencies unavailable

Version: 2.8.0
"""

import json
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple, Union

# Check for optional dependencies
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    px = None
    go = None
    PLOTLY_AVAILABLE = False

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    umap = None
    UMAP_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False



# Color palette for clusters
CLUSTER_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def _get_cluster_colors(cluster_assignments: List[str]) -> List[str]:
    """Map cluster names to colors."""
    unique_clusters = list(dict.fromkeys(cluster_assignments))
    cluster_to_color = {
        c: CLUSTER_COLORS[i % len(CLUSTER_COLORS)]
        for i, c in enumerate(unique_clusters)
    }
    return [cluster_to_color[c] for c in cluster_assignments]

@dataclass
class VisualizationConfig:
    """Configuration for embedding visualization."""
    n_neighbors: int = 15
    min_dist: float = 0.1
    metric: str = "cosine"
    n_components: int = 2
    random_state: Optional[int] = 42
    title: str = "Embedding Visualization"
    width: int = 800
    height: int = 600
    
    def __post_init__(self):
        if self.n_neighbors <= 0:
            raise ValueError("n_neighbors must be positive")
        if self.min_dist < 0:
            raise ValueError("min_dist must be non-negative")
        if self.n_components not in (2, 3):
            raise ValueError("n_components must be 2 or 3")


class EmbeddingReducer:
    """Reduces high-dimensional embeddings to 2D or 3D for visualization."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None, force_fallback: bool = False):
        self.config = config or VisualizationConfig()
        self.force_fallback = force_fallback
        self._use_umap = UMAP_AVAILABLE and not force_fallback
    
    def reduce(self, embeddings: Dict[str, List[float]]) -> Dict[str, Tuple[float, ...]]:
        """Reduce embeddings to n_components dimensions."""
        if not embeddings:
            return {}
        
        ids = list(embeddings.keys())
        vectors = [embeddings[id_] for id_ in ids]
        
        if len(ids) == 1:
            return {ids[0]: tuple([0.0] * self.config.n_components)}
        
        if self._use_umap and NUMPY_AVAILABLE:
            return self._reduce_umap(ids, vectors)
        else:
            return self._reduce_fallback(ids, vectors)
    
    def _reduce_umap(self, ids: List[str], vectors: List[List[float]]) -> Dict[str, Tuple[float, ...]]:
        """Reduce using UMAP algorithm."""
        X = np.array(vectors)
        n_neighbors = min(self.config.n_neighbors, len(ids) - 1)
        n_neighbors = max(n_neighbors, 2)
        
        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=self.config.min_dist,
            metric=self.config.metric,
            n_components=self.config.n_components,
            random_state=self.config.random_state,
        )
        
        coords = reducer.fit_transform(X)
        return {id_: tuple(coords[i].tolist()) for i, id_ in enumerate(ids)}
    
    def _reduce_fallback(self, ids: List[str], vectors: List[List[float]]) -> Dict[str, Tuple[float, ...]]:
        """Fallback: Simple PCA-like projection."""
        n_dims = len(vectors[0])
        n_points = len(vectors)
        n_components = self.config.n_components
        
        means = [sum(v[d] for v in vectors) / n_points for d in range(n_dims)]
        centered = [[v[d] - means[d] for d in range(n_dims)] for v in vectors]
        
        variances = []
        for d in range(n_dims):
            var = sum(c[d] ** 2 for c in centered) / n_points
            variances.append((var, d))
        
        variances.sort(reverse=True)
        top_dims = [d for _, d in variances[:n_components]]
        
        result = {}
        for i, id_ in enumerate(ids):
            coords = tuple(centered[i][d] for d in top_dims)
            result[id_] = coords
        
        return result


class EmbeddingVisualizer:
    """Creates interactive visualizations of embeddings."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.reducer = EmbeddingReducer(self.config)
    
    def visualize(
        self,
        embeddings: Dict[str, List[float]],
        labels: Optional[Dict[str, str]] = None,
        colors: Optional[Dict[str, str]] = None,
        clusters: Optional[Dict[str, str]] = None,
    ) -> Optional[Any]:
        """Create interactive visualization of embeddings."""
        if not embeddings:
            return None
        
        coords = self.reducer.reduce(embeddings)
        
        ids = list(coords.keys())
        x_vals = [coords[id_][0] for id_ in ids]
        y_vals = [coords[id_][1] for id_ in ids]
        z_vals = [coords[id_][2] for id_ in ids] if self.config.n_components == 3 else None
        
        label_vals = [labels.get(id_, id_) if labels else id_ for id_ in ids]
        
        if clusters:
            cluster_assignments = [clusters.get(id_, "unknown") for id_ in ids]
            color_vals = _get_cluster_colors(cluster_assignments)
        elif colors:
            color_vals = [colors.get(id_, "blue") for id_ in ids]
        else:
            color_vals = None
        
        if PLOTLY_AVAILABLE:
            return self._create_plotly_figure(ids, x_vals, y_vals, z_vals, label_vals, color_vals)
        else:
            return self._create_fallback_figure(ids, x_vals, y_vals, z_vals, label_vals, color_vals)
    
    def _create_plotly_figure(
        self,
        ids: List[str],
        x_vals: List[float],
        y_vals: List[float],
        z_vals: Optional[List[float]],
        label_vals: List[str],
        color_vals: Optional[List[str]],
    ) -> Any:
        """Create Plotly figure."""
        if z_vals:
            fig = go.Figure(data=[go.Scatter3d(
                x=x_vals, y=y_vals, z=z_vals,
                mode="markers",
                marker=dict(size=8, color=color_vals if color_vals else "blue", opacity=0.8),
                text=label_vals,
                hovertemplate="<b>%{text}</b><br>x: %{x:.2f}<br>y: %{y:.2f}<br>z: %{z:.2f}<extra></extra>",
            )])
        else:
            fig = go.Figure(data=[go.Scatter(
                x=x_vals, y=y_vals,
                mode="markers",
                marker=dict(size=10, color=color_vals if color_vals else "blue", opacity=0.8),
                text=label_vals,
                hovertemplate="<b>%{text}</b><br>x: %{x:.2f}<br>y: %{y:.2f}<extra></extra>",
            )])
        
        fig.update_layout(
            title=self.config.title,
            width=self.config.width,
            height=self.config.height,
        )
        
        return fig
    
    def _create_fallback_figure(
        self,
        ids: List[str],
        x_vals: List[float],
        y_vals: List[float],
        z_vals: Optional[List[float]],
        label_vals: List[str],
        color_vals: Optional[List[str]],
    ) -> Any:
        """Create fallback figure object without Plotly."""
        class FallbackFigure:
            def __init__(self, data):
                self.data = data
            
            def to_dict(self):
                return self.data
            
            def to_json(self):
                return json.dumps(self.data)
        
        data = {
            "type": "scatter" + ("3d" if z_vals else ""),
            "points": [
                {
                    "id": id_,
                    "x": x,
                    "y": y,
                    "z": z if z_vals else None,
                    "label": label,
                    "color": color if color_vals else "blue",
                }
                for id_, x, y, z, label, color in zip(
                    ids, x_vals, y_vals,
                    z_vals or [None] * len(ids),
                    label_vals,
                    color_vals or ["blue"] * len(ids),
                )
            ],
            "title": self.config.title,
            "width": self.config.width,
            "height": self.config.height,
        }
        
        return FallbackFigure(data)
    
    def save_html(self, figure: Any, path: str) -> None:
        """Save figure to HTML file."""
        if PLOTLY_AVAILABLE and hasattr(figure, "write_html"):
            figure.write_html(path)
        else:
            data = figure.to_dict() if hasattr(figure, "to_dict") else figure
            html = f'''<!DOCTYPE html>
<html>
<head><title>{self.config.title}</title></head>
<body>
<h1>{self.config.title}</h1>
<pre>{json.dumps(data, indent=2)}</pre>
</body>
</html>'''
            with open(path, "w") as f:
                f.write(html)
    
    def to_json(self, figure: Any) -> Union[str, dict]:
        """Convert figure to JSON."""
        if hasattr(figure, "to_json"):
            return figure.to_json()
        elif hasattr(figure, "to_dict"):
            return figure.to_dict()
        return {}
