#!/usr/bin/env python3
import os
import sys

# Ensure src is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.orchestrator import handle_connection

if __name__ == "__main__":
    try:
        handle_connection()
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
                f.write("deployment_status=failed\n")
        sys.exit(1)
