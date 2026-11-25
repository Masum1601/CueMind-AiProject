"""CueMind: 60-Second Rack Attack Duel.

Run:  python main.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.app import App  # noqa: E402

if __name__ == "__main__":
    App().run()
