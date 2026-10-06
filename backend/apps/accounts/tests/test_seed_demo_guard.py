"""Regression tests: seed_demo must never create a known-password superuser in production."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_refuses_to_run_when_debug_false(settings, monkeypatch):
    settings.DEBUG = False
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)
    with pytest.raises(CommandError, match="DEBUG=False"):
        call_command("seed_demo")
    assert not User.objects.filter(username="admin").exists()


@pytest.mark.parametrize(
    "admin_pw,user_pw",
    [("", ""), ("admin12345", "a-strong-user-pass-1"), ("a-strong-admin-pass", "demo12345"), ("short", "alsoshort")],
)
def test_production_flag_rejects_missing_or_weak_passwords(settings, monkeypatch, admin_pw, user_pw):
    settings.DEBUG = False
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", admin_pw)
    monkeypatch.setenv("DEMO_USER_PASSWORD", user_pw)
    with pytest.raises(CommandError):
        call_command("seed_demo", "--allow-production")
    assert not User.objects.filter(username="admin").exists()


def test_production_flag_uses_env_passwords(settings, monkeypatch):
    settings.DEBUG = False
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "prod-admin-Xq7!long")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "prod-user-Zp4!long")
    call_command("seed_demo", "--allow-production")
    admin = User.objects.get(username="admin")
    assert admin.check_password("prod-admin-Xq7!long")
    assert not admin.check_password("admin12345")
    assert User.objects.get(username="james_farmer").check_password("prod-user-Zp4!long")


def test_debug_keeps_local_dev_defaults(settings, monkeypatch):
    settings.DEBUG = True
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)
    call_command("seed_demo")
    assert User.objects.get(username="james_farmer").check_password("demo12345")
