from collections.abc import Iterator

import pytest

from src.admin import cli


def answer(monkeypatch: pytest.MonkeyPatch, inputs: list[str], passwords: list[str]) -> None:
    input_answers: Iterator[str] = iter(inputs)
    password_answers: Iterator[str] = iter(passwords)
    monkeypatch.setattr("builtins.input", lambda _: next(input_answers))
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: next(password_answers))


@pytest.mark.case(id="ADMIN-CLI-001")
def test_create_admin_prompt_validates_input(monkeypatch: pytest.MonkeyPatch) -> None:
    names = ["Админов", "Админ", ""]

    answer(monkeypatch, [" Root@Example.COM ", *names], ["root-password-1", "root-password-1"])
    new_admin = cli.ask_new_admin()
    assert new_admin.email == "root@example.com"
    assert new_admin.middle_name is None

    answer(monkeypatch, ["not-an-email", *names], [])
    with pytest.raises(SystemExit, match="Некорректная почта"):
        cli.ask_new_admin()

    for password in ("short", "x" * 33):
        answer(monkeypatch, ["root@example.com", *names], [password])
        with pytest.raises(SystemExit, match="Пароль должен быть от 8 до 32"):
            cli.ask_new_admin()

    answer(monkeypatch, ["root@example.com", *names], ["root-password-1", "other-password"])
    with pytest.raises(SystemExit, match="Пароли не совпадают"):
        cli.ask_new_admin()
