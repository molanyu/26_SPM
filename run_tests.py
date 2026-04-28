from __future__ import annotations

import argparse

import pytest

CORE_MODULE_TEST_TARGETS = [
    "tests/identity",
    "tests/resource",
    "tests/system_config",
    "tests/reservation",
    "tests/checkin",
    "tests/violation",
    "tests/notification",
    "tests/assistant",
]
ADMIN_PORTAL_TEST_TARGETS = [
    "tests/admin_portal",
]
POSTGRES_TEST_TARGETS = [
    "tests/postgres",
]
SCENARIO_TEST_TARGETS = [
    "tests/scenario",
]
UNIT_TEST_TARGETS = [
    "tests/test_run_tests.py",
]
COMMON_PYTEST_ARGS = [
    "-q",
    "-p",
    "no:cacheprovider",
]

SUITE_TARGETS = {
    "unit": UNIT_TEST_TARGETS,
    "integration": CORE_MODULE_TEST_TARGETS + ADMIN_PORTAL_TEST_TARGETS,
    "postgres": POSTGRES_TEST_TARGETS,
    "scenario": SCENARIO_TEST_TARGETS,
    "all": UNIT_TEST_TARGETS + CORE_MODULE_TEST_TARGETS + ADMIN_PORTAL_TEST_TARGETS,
}


def build_pytest_args(suite: str) -> list[str]:
    if suite not in SUITE_TARGETS:
        raise ValueError(f"Unsupported suite: {suite}")
    return [*COMMON_PYTEST_ARGS, *SUITE_TARGETS[suite]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the unified project test suites.")
    parser.add_argument(
        "--suite",
        choices=tuple(SUITE_TARGETS.keys()),
        default="all",
        help="Select which test suite to run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return pytest.main(build_pytest_args(args.suite))


if __name__ == "__main__":
    raise SystemExit(main())
