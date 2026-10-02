"""
Baseline Safety Tests: Validates C: drive restrictions and voice confirmation policies.
Total test count: 24 tests.
"""
import pytest
from ellie.safety import SafetyGate, SafetyResult


class TestPathSafety:
    """17 path safety test cases."""

    @pytest.mark.parametrize(
        "blocked_path",
        [
            r"C:\Windows\System32",
            "C:/Users/test",
            r"c:\temp",
            "c:/",
            "C:",
            "c:anything",
            r"C:\ ",
            "C://",
            r"C:\Program Files\app",
            "C:\\Users/test/file.txt",
            r"c:/Windows\System32",
            r"C:\secret.txt",
        ],
    )
    def test_c_drive_blocked(self, blocked_path):
        gate = SafetyGate()
        allowed, reason = gate.check_path(blocked_path)
        assert allowed is False
        assert "drive C:" in reason or "blocked" in reason.lower()

    @pytest.mark.parametrize(
        "allowed_path",
        [
            r"D:\Projects\test.txt",
            "D:/data/file.csv",
            r"E:\backup",
            r"d:\users\docs",
            "F:/media/video.mp4",
        ],
    )
    def test_non_c_drive_allowed(self, allowed_path):
        gate = SafetyGate()
        allowed, reason = gate.check_path(allowed_path)
        assert allowed is True


class TestActionSafety:
    """7 action safety test cases."""

    def test_confirmation_required_send_message(self):
        gate = SafetyGate()
        res = gate.check_action("send_message")
        assert res.allowed is True
        assert res.needs_confirmation is True

    def test_confirmation_required_delete_file(self):
        gate = SafetyGate()
        res = gate.check_action("delete_file")
        assert res.allowed is True
        assert res.needs_confirmation is True

    def test_open_app_allowed(self):
        gate = SafetyGate()
        res = gate.check_action("open_app")
        assert res.allowed is True
        assert res.needs_confirmation is False

    def test_blocked_action_run_shell(self):
        gate = SafetyGate()
        res = gate.check_action("run_shell")
        assert res.allowed is False
        assert res.blocked_reason == "BLOCKED_ACTION"

    def test_blocked_action_install_software(self):
        gate = SafetyGate()
        res = gate.check_action("install_software")
        assert res.allowed is False
        assert res.blocked_reason == "BLOCKED_ACTION"

    def test_file_path_safety_check_blocked(self):
        gate = SafetyGate()
        res = gate.check_action("read_file", entities={"file_path": r"C:\secret.txt"})
        assert res.allowed is False
        assert res.blocked_reason == "RESTRICTED_DRIVE"

    def test_file_path_safety_check_allowed(self):
        gate = SafetyGate()
        res = gate.check_action("read_file", entities={"file_path": r"D:\docs\readme.txt"})
        assert res.allowed is True
        assert res.needs_confirmation is False
