#!/usr/bin/env python3
"""
run_all.py - Starts the chat server and bot swarm together.
"""

import subprocess
import time
import sys

def main():
    print("Starting chat server...")
    server_process = subprocess.Popen([sys.executable, "server.py"])

    # Wait a bit for server to start
    time.sleep(2)

    print("Starting bot swarm...")
    try:
        subprocess.run([sys.executable, "bot_swarm.py"])
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()