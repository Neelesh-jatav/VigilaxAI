from typing import Dict, List


def map_camera_names(cameras: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Hook for future OS-specific camera name mapping."""
    return cameras
