from __future__ import annotations

import run_tests


def test_build_pytest_args_for_all_suite_uses_unified_targets() -> None:
    args = run_tests.build_pytest_args("all")

    assert args[:3] == ["-q", "-p", "no:cacheprovider"]
    assert args[3:] == [
        "tests/test_run_tests.py",
        "tests/identity",
        "tests/resource",
        "tests/system_config",
        "tests/reservation",
        "tests/checkin",
        "tests/violation",
        "tests/notification",
        "tests/assistant",
        "tests/admin_portal",
    ]


def test_build_pytest_args_for_integration_suite_excludes_unit_targets() -> None:
    args = run_tests.build_pytest_args("integration")

    assert "tests/test_run_tests.py" not in args
    assert args[3:] == [
        "tests/identity",
        "tests/resource",
        "tests/system_config",
        "tests/reservation",
        "tests/checkin",
        "tests/violation",
        "tests/notification",
        "tests/assistant",
        "tests/admin_portal",
    ]


def test_main_delegates_to_pytest_with_selected_suite(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_pytest_main(args: list[str]) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(run_tests.pytest, "main", fake_pytest_main)

    exit_code = run_tests.main(["--suite", "unit"])

    assert exit_code == 0
    assert captured["args"] == [
        "-q",
        "-p",
        "no:cacheprovider",
        "tests/test_run_tests.py",
    ]


def test_build_pytest_args_for_postgres_suite_uses_postgres_targets() -> None:
    args = run_tests.build_pytest_args("postgres")

    assert args[:3] == ["-q", "-p", "no:cacheprovider"]
    assert args[3:] == [
        "tests/postgres",
    ]


def test_build_pytest_args_for_scenario_suite_uses_scenario_targets() -> None:
    args = run_tests.build_pytest_args("scenario")

    assert args[:3] == ["-q", "-p", "no:cacheprovider"]
    assert args[3:] == [
        "tests/scenario",
    ]
    assert "tests/scenario" not in run_tests.build_pytest_args("all")
