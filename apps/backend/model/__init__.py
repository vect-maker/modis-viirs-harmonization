try:
    from .ClusterHotspot import ClusterHotspots
    from .EnvironmentalRecord import EnvironmentalRecord
    from .FireCluster import FireCluster
    from .Hotspots import Hotspots
except ImportError:
    from model.ClusterHotspot import ClusterHotspots
    from model.EnvironmentalRecord import EnvironmentalRecord
    from model.FireCluster import FireCluster
    from model.Hotspots import Hotspots

__all__ = [
    "ClusterHotspots",
    "EnvironmentalRecord",
    "FireCluster",
    "Hotspots",
]
