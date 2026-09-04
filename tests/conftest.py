import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Some application modules initialise a DatabaseWriter during import. Isolate
# those side effects before pytest imports any test modules so a local test run
# cannot migrate or write the operator's tender database or runtime output.
TEST_RUNTIME_DIR = Path(tempfile.mkdtemp(prefix="tender-intelligence-tests-"))
os.environ.update(
    {
        "DB_PATH": str(TEST_RUNTIME_DIR / "tenders.db"),
        "OUTPUT_DIR": str(TEST_RUNTIME_DIR / "output"),
        "ACTIVE_TENDERS_DIR": str(TEST_RUNTIME_DIR / "active_tenders"),
        "LOG_FILE": str(TEST_RUNTIME_DIR / "logs" / "test.log"),
    }
)
