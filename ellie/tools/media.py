"""Media control tools for Ellie."""
import logging
from ellie.tools import register

logger = logging.getLogger(__name__)

try:
    import pyautogui
except ImportError:
    logger.warning("pyautogui not installed; media key controls may fail.")

def _fallback_volume_control(action: str) -> str:
    """Fallback volume control using pyautogui when pycaw fails."""
    try:
        if action == 'up':
            pyautogui.press('volumeup', presses=5)
            return "Volume increased"
        elif action == 'down':
            pyautogui.press('volumedown', presses=5)
            return "Volume decreased"
        elif action == 'mute' or action == 'unmute':
            pyautogui.press('volumemute')
            return f"Volume {action}d"
        return "Action not supported in fallback mode"
    except Exception as e:
        return f"Error in fallback volume control: {e}"

def set_volume(step: dict) -> str:
    """Set system volume using pycaw, falling back to pyautogui."""
    action = step.get('action', '').lower()
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        if action == 'up':
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
            return "Volume increased by 10%"
        elif action == 'down':
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
            return "Volume decreased by 10%"
        elif action == 'mute':
            volume.SetMute(1, None)
            return "Volume muted"
        elif action == 'unmute':
            volume.SetMute(0, None)
            return "Volume unmuted"
        elif action == 'set':
            val = float(step.get('value', 50)) / 100.0
            volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, val)), None)
            return f"Volume set to {step.get('value')}%"
        return f"Unknown volume action: {action}"
    except Exception as e:
        logger.warning(f"Pycaw error, using fallback: {e}")
        return _fallback_volume_control(action)

def media_control(step: dict) -> str:
    """Control media playback via virtual keypresses."""
    action = step.get('action', '').lower()
    try:
        if action in ['play', 'pause', 'playpause']:
            pyautogui.press('playpause')
        elif action == 'next':
            pyautogui.press('nexttrack')
        elif action == 'previous':
            pyautogui.press('prevtrack')
        elif action == 'stop':
            pyautogui.press('stop')
        else:
            return f"Unknown media action: {action}"
        return f"Media {action}"
    except Exception as e:
        logger.error(f"Error controlling media: {e}")
        return f"Error controlling media: {e}"

# Register media tools
register('set_volume', set_volume)
register('media_control', media_control)
