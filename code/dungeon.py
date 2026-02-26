#!/usr/bin/env python3
"""
DUNGEON CRAWLER — entry point.
All game logic lives in the dungeon/ modules.
"""

import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from game import run_game


def main():
    while run_game():
        pass


if __name__ == '__main__':
    main()
