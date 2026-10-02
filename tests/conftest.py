"""
Ellie test suite root marker and shared test configuration.
"""
import pytest
import os
import sys

# Ensure Ellie root is on sys.path
ELLIE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ELLIE_ROOT not in sys.path:
    sys.path.insert(0, ELLIE_ROOT)

venv_site = r"D:\Ellie\venv\Lib\site-packages"
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)
