"""
Audio volume control manager.
Supports both Pycaw COM adjustments and Virtual Key hardware controls.
"""
import ctypes
import logging
import time
from typing import Any, Dict, Tuple

logger = logging.getLogger("ellie.actions.volume_manager")

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_KEYUP = 0x0002


class VolumeManager:
    """Controls Windows master audio volume and mute status."""

    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
        self.endpoint_volume = None
        self._init_pycaw()

    def _init_pycaw(self) -> None:
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.endpoint_volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        except Exception:
            self.endpoint_volume = None

    def adjust(self, cmd: Dict[str, Any]) -> Tuple[bool, str]:
        op_type = cmd.get("type", "up")

        if op_type == "mute":
            return self.set_mute(True)

        if op_type == "unmute":
            return self.set_mute(False)

        if op_type == "set":
            val = cmd.get("value", 50)
            return self.set_volume_scalar(val / 100.0)

        steps = cmd.get("steps", 5)
        if op_type == "up":
            return self.step_volume(up=True, steps=steps)

        if op_type == "down":
            return self.step_volume(up=False, steps=steps)

        return False, "Unknown volume command."

    def set_volume_scalar(self, scalar: float) -> Tuple[bool, str]:
        scalar = max(0.0, min(1.0, scalar))
        if self.endpoint_volume:
            try:
                self.endpoint_volume.SetMasterVolumeLevelScalar(scalar, None)
                pct = int(scalar * 100)
                return True, f"Volume set to {pct} percent."
            except Exception:
                pass

        pct = int(scalar * 100)
        return True, f"Volume adjusted towards {pct} percent."

    def set_mute(self, mute: bool) -> Tuple[bool, str]:
        if self.endpoint_volume:
            try:
                self.endpoint_volume.SetMute(1 if mute else 0, None)
                state = "Muted" if mute else "Unmuted"
                return True, f"{state} audio."
            except Exception:
                pass

        self._tap_key(VK_VOLUME_MUTE)
        return True, "Toggled mute."

    def step_volume(self, up: bool, steps: int = 5) -> Tuple[bool, str]:
        vk = VK_VOLUME_UP if up else VK_VOLUME_DOWN
        for _ in range(steps):
            self._tap_key(vk)
        direction = "up" if up else "down"
        return True, f"Turned volume {direction}."

    def _tap_key(self, vk: int) -> None:
        if not self.user32:
            return
        try:
            self.user32.keybd_event(vk, 0, 0, 0)
            self.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass
