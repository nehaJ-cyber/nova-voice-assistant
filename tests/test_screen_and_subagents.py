"""
Baseline Screen Perception and Subagent Management Tests.
Total test count: 7 tests.
"""
from unittest.mock import patch
from ellie.screen import (
    get_active_window,
    inspect_screen,
    click_element_enter,
    scroll_screen,
    get_running_browser,
)
from ellie.subagents import SubagentManager
from ellie.safety import SafetyGate


def test_get_active_window():
    win = get_active_window()
    assert isinstance(win, dict)
    assert "hwnd" in win
    assert "title" in win


def test_inspect_screen():
    info = inspect_screen()
    assert isinstance(info, dict)
    assert "active_window" in info
    assert "elements_count" in info
    assert info["elements_count"] >= 0


def test_click_element_enter():
    success = click_element_enter("OK_Button")
    assert success is True


def test_scroll_screen():
    with patch("ctypes.windll.user32.mouse_event", create=True):
        res = scroll_screen("down", amount=3)
        assert res is True


def test_get_running_browser():
    browser = get_running_browser()
    # Returns string or None
    assert browser is None or isinstance(browser, str)


def test_subagent_manager_spawning():
    mgr = SubagentManager()
    started = mgr.deploy_subagent("test_agent_1", "index files")
    assert started is True
    status = mgr.get_status("test_agent_1")
    assert status is not None
    assert status["task"] == "index files"


def test_safety_confirmation_on_subagent():
    gate = SafetyGate()
    res = gate.check_action("deploy_subagent")
    assert res.allowed is True
    assert res.needs_confirmation is True
