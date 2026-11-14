try:
    from .ClusterHotspot import ClusterHotspots
    from .EnvironmentalRecord import EnvironmentalRecord
    from .FireCluster import FireCluster
    from .FireClusterForecast import FireClusterForecast
    from .Hotspots import Hotspots
except ImportError:
    from model.ClusterHotspot import ClusterHotspots
    from model.EnvironmentalRecord import EnvironmentalRecord
    from model.FireCluster import FireCluster
    from model.FireClusterForecast import FireClusterForecast
    from model.Hotspots import Hotspots

__all__ = [
    "ClusterHotspots",
    "EnvironmentalRecord",
    "FireCluster",
    "FireClusterForecast",
    "Hotspots",
]
