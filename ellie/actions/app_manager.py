"""
Application launch and termination manager.
Handles registry App Paths lookup, shortcut resolution, detached process spawning,
graceful WM_CLOSE signals, and safety boundary validation.
"""
import ctypes
import logging
import os
import subprocess
try:
    import winreg
except ImportError:
    winreg = None
from typing import Optional, Tuple
import psutil

logger = logging.getLogger("ellie.actions.app_manager")

DANGEROUS_BINARIES = {
    "format.com", "diskpart.exe", "reg.exe", "regedit.exe",
    "bcdedit.exe", "vssadmin.exe", "cipher.exe", "sfc.exe"
}

PROTECTED_PROCESSES = {
    "explorer.exe", "dwm.exe", "csrss.exe", "lsass.exe",
    "services.exe", "svchost.exe", "smss.exe", "wininit.exe"
}


class AppManager:
    """Manages launching and closing Windows desktop applications."""

    def resolve_executable_path(self, app_name: str) -> Optional[str]:
        clean_name = app_name.lower().strip()
        if not clean_name.endswith((".exe", ".cmd", ".com", ".bat", ".vbs")):
            exe_candidate = clean_name + ".exe"
        else:
            exe_candidate = clean_name

        if winreg is not None:
            path = self._query_reg_app_paths(winreg.HKEY_CURRENT_USER, exe_candidate)
            if path and os.path.exists(path):
                return path

            path = self._query_reg_app_paths(winreg.HKEY_LOCAL_MACHINE, exe_candidate)
            if path and os.path.exists(path):
                return path

        sys32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", exe_candidate)
        if os.path.exists(sys32):
            return sys32

        return exe_candidate

    def _query_reg_app_paths(self, root_key: int, exe_name: str) -> Optional[str]:
        if winreg is None:
            return None
        sub_key = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exe_name}"
        try:
            with winreg.OpenKey(root_key, sub_key) as key:
                val, _ = winreg.QueryValueEx(key, "")
                return val
        except (FileNotFoundError, OSError):
            return None

    def launch(self, app_name: str) -> Tuple[bool, str]:
        target = self.resolve_executable_path(app_name)
        base = os.path.basename(target).lower()
        raw_base = os.path.basename(app_name).lower()
        if raw_base in DANGEROUS_BINARIES or base in DANGEROUS_BINARIES:
            logger.warning("Blocked launch of blacklisted executable: %s", base)
            return False, f"Opening {app_name} is restricted by system safety policy."

        try:
            DETACHED_FLAGS = 0x00000008 | 0x00000200
            subprocess.Popen([target], creationflags=DETACHED_FLAGS, shell=False)
            friendly_name = base.replace(".exe", "").capitalize()
            return True, f"Opening {friendly_name}."
        except FileNotFoundError:
            try:
                os.startfile(app_name)
                return True, f"Opening {app_name}."
            except Exception as e:
                return False, f"Could not find application {app_name}."
        except Exception as e:
            return False, f"Failed to open {app_name}: {str(e)}"

    def close(self, app_name: str) -> Tuple[bool, str]:
        clean_name = os.path.basename(app_name).lower().replace(".exe", "")

        if clean_name + ".exe" in PROTECTED_PROCESSES or clean_name in PROTECTED_PROCESSES:
            return False, f"Cannot close core system process {clean_name}."

        matched_pids = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = proc.info["name"].lower()
                if clean_name in pname:
                    matched_pids.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not matched_pids:
            return False, f"No running application found matching {clean_name}."

        closed_windows = self._post_wm_close_to_pids(matched_pids)

        for pid in matched_pids:
            try:
                p = psutil.Process(pid)
                if p.is_running():
                    p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        friendly_name = clean_name.capitalize()
        return True, f"Closed {friendly_name}."

    def _post_wm_close_to_pids(self, pids: list) -> int:
        WM_CLOSE = 0x0010
        closed_count = 0
        try:
            user32 = ctypes.windll.user32
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def enum_cb(hwnd, lparam):
                nonlocal closed_count
                lpdw_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_pid))
                if lpdw_pid.value in pids and user32.IsWindowVisible(hwnd):
                    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                    closed_count += 1
                return True

            cb = WNDENUMPROC(enum_cb)
            user32.EnumWindows(cb, 0)
        except Exception:
            pass
        return closed_count
