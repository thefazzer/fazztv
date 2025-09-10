"""Media processing modules for FazzTV."""

from fazztv.processors.video import VideoProcessor
from fazztv.processors.audio import AudioProcessor
from fazztv.processors.overlay import OverlayManager
from fazztv.processors.equalizer import EqualizerGenerator

__all__ = [
    'VideoProcessor',
    'AudioProcessor', 
    'OverlayManager',
    'EqualizerGenerator'
]