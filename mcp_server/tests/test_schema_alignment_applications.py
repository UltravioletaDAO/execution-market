"""
Tests for applications table schema alignment helper.
"""

from types import SimpleNamespace

import pytest

from .. import supabase_client as db


class _ProbeQuery:
    def __init__(self, fail: bool = False):
        self.fail = fail

    def select(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.fail:
            raise Exception("relation does not exist")
        return SimpleNamespace(data=[])


class _ProbeClient:
    def __init__(self, missing_tables=None):
        self.missing_tables = set(missing_tables or [])
        self.calls = []

    def table(self, name: str):
        self.calls.append(name)
        return _ProbeQuery(fail=name in self.missing_tables)


def _reset_cache():
    db._applications_table_name = None


def test_applications_table_prefers_task_applications(monkeypatch):
    _reset_cache()
    client = _ProbeClient()
    monkeypatch.setattr(db, "get_client", lambda: client)

    table_name = db.get_applications_table_name()

    assert table_name == "task_applications"
    assert client.calls[0] == "task_applications"


def test_applications_table_falls_back_to_legacy(monkeypatch):
    _reset_cache()
    client = _ProbeClient(missing_tables={"task_applications"})
    monkeypatch.setattr(db, "get_client", lambda: client)

    table_name = db.get_applications_table_name()

    assert table_name == "applications"
    assert client.calls[:2] == ["task_applications", "applications"]
