import subprocess
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
env = os.environ.copy()
env['PYTHONPATH'] = 'D:\\Ellie'
env['PYTHONIOENCODING'] = 'utf-8'
subprocess.Popen([os.path.join('venv', 'Scripts', 'python.exe'), '-m', 'ellie.main'], env=env, creationflags=subprocess.CREATE_NO_WINDOW)
