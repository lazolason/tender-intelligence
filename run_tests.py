import pytest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    # Run pytest on the tests directory
    # Disable plugins that might cause issues
    sys.exit(pytest.main(["-v", "-p", "no:cov", "-p", "no:hydra-core", "tests"]))
