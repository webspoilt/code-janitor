"""
Hardware resource management and monitoring.
"""

import logging
import psutil
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
# GPUtil removed for serverless compatibility
GPUtil = None

logger = logging.getLogger(__name__)

@dataclass
class HardwareProfile:
    """Hardware configuration limits."""
    max_gpu_memory_mb: int = 4096
    max_ram_percent: int = 70
    max_cpu_threads: int = 4
    model_context_window: int = 4096

    @property
    def dict(self):
        return asdict(self)

class ResourceManager:
    """Manages hardware resources and monitoring."""
    
    def __init__(self, profile: Optional[HardwareProfile] = None):
        self.profile = profile or HardwareProfile()
        
    def get_status(self) -> Dict[str, Any]:
        """Get current hardware utilization."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_threads = psutil.cpu_count()
        
        # RAM
        ram = psutil.virtual_memory()
        
        # GPU
        gpu_status = {"available": False, "memory_mb": 0, "utilization": 0}
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_status.update({
                        "available": True,
                        "memory_mb": gpu.memoryUsed,
                        "utilization": gpu.memoryUtil * 100
                    })
            except Exception:
                pass

        return {
            "cpu": {
                "percent": cpu_percent,
                "threads": cpu_threads
            },
            "ram": {
                "percent": ram.percent,
                "used_mb": round(ram.used / (1024 * 1024), 1),
                "total_mb": round(ram.total / (1024 * 1024), 1)
            },
            "gpu": gpu_status,
            "limits": self.profile.dict
        }

    def check_resources(self, estimated_ram_mb: int = 1000) -> bool:
        """Check if sufficient resources are available."""
        status = self.get_status()
        
        # Check RAM headroom
        available_ram = status['ram']['total_mb'] - status['ram']['used_mb']
        if available_ram < estimated_ram_mb:
            return False
            
        if status['ram']['percent'] > self.profile.max_ram_percent:
            return False
            
        return True
