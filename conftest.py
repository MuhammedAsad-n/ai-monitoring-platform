"""
Pytest configuration — shared fixtures for the entire test suite.
Works on Windows, Mac, and Linux.
"""

import asyncio
import os
import tempfile
import pytest

# ── Set environment BEFORE any project modules are imported ─────────────────
# tempfile.gettempdir() returns the correct temp folder for every OS:
#   Windows  → C:\Users\<name>\AppData\Local\Temp
#   Mac/Linux → /tmp
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "test_monitoring.db")

os.environ["DB_PATH"]           = TEST_DB_PATH
os.environ["SIMULATE_TRAFFIC"]  = "false"
os.environ["ENVIRONMENT"]       = "test"


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop shared across the entire test session."""
    policy = asyncio.DefaultEventLoopPolicy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database(event_loop):
    """
    Initialize the test database synchronously via the session event loop.
    Using a synchronous fixture (not async) avoids the
    'coroutine was never awaited' RuntimeWarning on pytest-asyncio strict mode.
    """
    from database.connection import init_db

    # Remove stale DB from any previous run
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Run the async init_db on the session loop — blocks until complete
    event_loop.run_until_complete(init_db())

    yield  # tests run here

    # Teardown — remove test DB after all tests finish
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass  # Windows sometimes holds the file briefly — safe to ignore
