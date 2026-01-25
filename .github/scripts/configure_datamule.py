#!/usr/bin/env python3
"""Configure datamule with API key from environment."""

import os
from datamule import Portfolio

def main():
    """Configure datamule API key."""
    api_key = os.environ.get('DATAMULE_API_KEY')
    
    if not api_key:
        print("Warning: DATAMULE_API_KEY not set. Will use SEC rate-limited endpoints.")
        return
    
    # Test that datamule is configured correctly
    try:
        portfolio = Portfolio('test')
        portfolio.set_api_key(api_key)
        print("✓ Datamule API key configured successfully")
    except Exception as e:
        print(f"✗ Error configuring datamule: {e}")
        raise

if __name__ == '__main__':
    main()