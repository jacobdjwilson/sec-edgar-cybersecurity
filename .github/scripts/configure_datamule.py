#!/usr/bin/env python3
"""
Configure datamule API key from environment variable.
Run this before other scripts when using the datamule provider.
"""

import os
import sys
import subprocess


def configure_datamule():
    api_key = os.environ.get("DATAMULE_API_KEY", "").strip()

    if not api_key:
        print("No DATAMULE_API_KEY found. Using SEC EDGAR direct API (rate limited to 7 req/s).")
        return False

    try:
        result = subprocess.run(
            ["datamule", "config", "--api-key", api_key],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("datamule API key configured successfully.")
            return True
        else:
            print(f"Warning: Failed to configure datamule API key: {result.stderr}")
            return False
    except FileNotFoundError:
        # datamule may expose config via Python API instead of CLI
        try:
            import datamule as dm
            if hasattr(dm, "set_api_key"):
                dm.set_api_key(api_key)
                print("datamule API key configured via Python API.")
                return True
            elif hasattr(dm, "config"):
                dm.config(api_key=api_key)
                print("datamule API key configured via Python config().")
                return True
            else:
                # Write to datamule config file directly
                config_dir = os.path.expanduser("~/.datamule")
                os.makedirs(config_dir, exist_ok=True)
                config_path = os.path.join(config_dir, "config.yml")
                import yaml
                config = {}
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        config = yaml.safe_load(f) or {}
                config["api_key"] = api_key
                with open(config_path, "w") as f:
                    yaml.dump(config, f)
                print(f"datamule API key written to {config_path}.")
                return True
        except Exception as e:
            print(f"Warning: Could not configure datamule API key: {e}")
            return False
    except Exception as e:
        print(f"Warning: Unexpected error configuring datamule: {e}")
        return False


if __name__ == "__main__":
    success = configure_datamule()
    sys.exit(0 if success else 1)
