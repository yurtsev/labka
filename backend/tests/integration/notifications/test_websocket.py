import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import cfg
from tests.support.auth import create_group
from tests.support.courses import create_student, sign_in
from tests.support.schedule import autumn_course
from tests.support.websocket import WebSocketClosedError, WebSocketSession


async def another_client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


@pytest.mark.case(id="UC-C6-004")
async def test_notification_is_pushed_to_the_addressee_only(
    app: FastAPI, client: AsyncClient, db: AsyncSession, realtime: None
) -> None:
    course, group = await autumn_course(client, db)
    async with await another_client(app) as other_client:
        await sign_in(other_client, "student@example.com", "password-1")
        stranger_group = await create_group(db, name="БВТ2602", code="CODE-2")
        await create_student(client, db, stranger_group, "CODE-2", "outsider@example.com")
        async with (
            WebSocketSession(app, other_client) as tab_one,
            WebSocketSession(app, other_client) as tab_two,
            WebSocketSession(app, client) as outsider,
        ):
            ready = await tab_one.receive_json()
            await tab_two.receive_json()
            outsider_ready = await outsider.receive_json()
            teacher = await another_client(app)
            async with teacher:
                await sign_in(teacher, "teacher@example.com", "password-1")
                created = await teacher.post(
                    f"/api/courses/{course['id']}/announcements", json={"text": "Привет"}
                )
                assert created.status_code == 201, created.text
                first = await tab_one.receive_json()
                second = await tab_two.receive_json()
                # Правка той же серии обновляет прежнее уведомление, а не добавляет новое.
                for _ in range(2):
                    await teacher.post(
                        f"/api/courses/{course['id']}/schedule/rules",
                        json={
                            "group_id": str(group.id),
                            "lesson_type": "lab",
                            "weekday": 2,
                            "slot": 1,
                            "repeat": "weekly",
                            "room": None,
                        },
                    )
                schedule = await tab_one.receive_json()
                schedule_again = await tab_one.receive_json()
            await tab_one.expect_silence()
            # Студент группы, которой нет в курсе, ничего не получает.
            await outsider.expect_silence(0.3)

    assert ready == {"type": "ready", "unread_count": 1}
    assert outsider_ready == {"type": "ready", "unread_count": 0}
    assert first == second
    assert first["type"] == "notification"
    assert first["unread_count"] == 2
    assert first["notification"]["title"] == "Новое объявление"
    assert first["notification"]["course"] == {"id": course["id"], "name": "Алгоритмы"}
    assert first["notification"]["target"]["section"] == "course_feed"
    assert first["notification"]["is_read"] is False
    assert schedule["notification"]["title"] == "Расписание изменено"
    assert schedule["unread_count"] == 3
    assert schedule_again["notification"]["id"] == schedule["notification"]["id"]
    assert schedule_again["unread_count"] == 3


@pytest.mark.case(id="UC-C6-005")
async def test_websocket_rejects_strangers(
    app: FastAPI, client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await autumn_course(client, db)
    anonymous = await another_client(app)
    async with anonymous:
        with pytest.raises(WebSocketClosedError) as no_cookie:
            async with WebSocketSession(app, anonymous) as session:
                await session.receive_json()
    with pytest.raises(WebSocketClosedError) as foreign_site:
        async with WebSocketSession(app, client, origin="http://evil.example") as session:
            await session.receive_json()
    monkeypatch.setattr(cfg.cors, "origins", ["http://localhost:3000"])
    async with WebSocketSession(app, client, origin="http://localhost:3000") as allowed:
        ready = await allowed.receive_json()
    async with WebSocketSession(app, client) as without_origin:
        no_origin_ready = await without_origin.receive_json()

    assert no_cookie.value.code == 4401
    assert foreign_site.value.code == 4403
    assert ready["type"] == no_origin_ready["type"] == "ready"


@pytest.mark.case(id="UC-C6-006")
async def test_revoked_session_closes_its_socket(
    app: FastAPI, client: AsyncClient, db: AsyncSession, realtime: None
) -> None:
    await autumn_course(client, db)
    async with await another_client(app) as phone, await another_client(app) as laptop:
        await sign_in(phone, "student@example.com", "password-1")
        await sign_in(laptop, "student@example.com", "password-1")
        async with (
            WebSocketSession(app, phone) as phone_socket,
            WebSocketSession(app, laptop) as laptop_socket,
        ):
            await phone_socket.receive_json()
            await laptop_socket.receive_json()

            # Смена пароля завершает остальные сессии, но не ту, где её сделали.
            changed = await phone.post(
                "/api/auth/password",
                json={"current_password": "password-1", "new_password": "password-2"},
            )
            with pytest.raises(WebSocketClosedError) as revoked:
                await laptop_socket.receive_json()
            await phone_socket.expect_silence(0.3)

            logout = await phone.post("/api/auth/logout")
            with pytest.raises(WebSocketClosedError) as logged_out:
                await phone_socket.receive_json()

    assert changed.status_code == 204, changed.text
    assert revoked.value.code == 4401
    assert logout.status_code == 204
    assert logged_out.value.code == 4401


@pytest.mark.case(id="UC-C6-007")
async def test_socket_pings_and_resyncs_after_database_connection_loss(
    app: FastAPI,
    client: AsyncClient,
    db: AsyncSession,
    realtime: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    course, _ = await autumn_course(client, db)
    monkeypatch.setattr(cfg.notifications, "websocket_ping_seconds", 0.3)
    async with await another_client(app) as student_client:
        await sign_in(student_client, "student@example.com", "password-1")
        async with WebSocketSession(app, student_client) as socket:
            await socket.receive_json()
            ping = await socket.receive_json()

            # Обрываем соединение слушателя: он переподключается и просит перечитать данные.
            await db.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                    " WHERE query LIKE 'LISTEN%' AND pid <> pg_backend_pid()"
                )
            )
            messages = []
            for _ in range(20):
                message = await socket.receive_json(timeout=5)
                messages.append(message["type"])
                if message["type"] == "resync":
                    break
            await asyncio.sleep(0.2)
            await client.post(f"/api/courses/{course['id']}/announcements", json={"text": "После"})
            after = None
            for _ in range(20):
                message = await socket.receive_json(timeout=5)
                if message["type"] == "notification":
                    after = message
                    break

    assert ping == {"type": "ping"}
    assert messages[-1] == "resync"
    assert after is not None and after["notification"]["title"] == "Новое объявление"
