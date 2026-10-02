"""
Baseline System and Application Tool Tests.
Total test count: 6 tests.
"""
from unittest.mock import patch
from ellie.tools.browser import open_browser, google_search
from ellie.tools.system import get_battery, get_current_time
from ellie.tools.files import read_file
from ellie.tools.apps import open_app


class TestBrowserTools:
    def test_open_browser(self):
        with patch("webbrowser.open", return_value=True) as mock_open:
            success, msg = open_browser("https://example.com")
            assert success is True
            mock_open.assert_called_once_with("https://example.com")

    def test_google_search(self):
        with patch("webbrowser.open", return_value=True) as mock_open:
            success, msg = google_search("test query")
            assert success is True
            assert "test+query" in mock_open.call_args[0][0]


class TestSystemInfo:
    def test_get_battery(self):
        status = get_battery()
        assert isinstance(status, str)
        assert len(status) > 0

    def test_get_current_time(self):
        curr_time = get_current_time()
        assert isinstance(curr_time, str)
        assert len(curr_time) > 0


class TestFileSafety:
    def test_read_file_c_drive_blocked(self):
        res = read_file(r"C:\Windows\System32\drivers\etc\hosts")
        assert "Safety Violation" in res

    def test_read_file_d_drive_allowed(self):
        # Even if not found, it must NOT be a Safety Violation
        res = read_file(r"D:\nonexistent_file_test_123.txt")
        assert "Safety Violation" not in res


class TestApps:
    def test_open_app_launches_process(self):
        with patch("subprocess.Popen") as mock_popen:
            success, msg = open_app("notepad.exe")
            assert success is True
            mock_popen.assert_called_once_with(["notepad.exe"], shell=False)
