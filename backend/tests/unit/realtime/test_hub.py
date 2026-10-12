from collections.abc import Mapping
from uuid import uuid7

import pytest

from src.core.realtime.hub import RealtimeHub


class FakeConnection:
    def __init__(self, broken: bool = False) -> None:
        self.sent: list[Mapping[str, object]] = []
        self.closed_with: int | None = None
        self._broken = broken

    async def send_json(self, data: Mapping[str, object]) -> None:
        if self._broken:
            raise ConnectionError
        self.sent.append(data)

    async def close(self, code: int) -> None:
        self.closed_with = code


@pytest.mark.case(id="REALTIME-HUB-001")
async def test_message_goes_to_every_connection_of_the_user_only() -> None:
    hub = RealtimeHub()
    user, other, session_a, session_b = uuid7(), uuid7(), uuid7(), uuid7()
    tab_one, tab_two, stranger = FakeConnection(), FakeConnection(), FakeConnection()
    hub.register(user, session_a, tab_one)
    hub.register(user, session_b, tab_two)
    hub.register(other, uuid7(), stranger)

    sent = await hub.send_to_user(user, {"type": "notification"})
    nobody = await hub.send_to_user(uuid7(), {"type": "notification"})

    assert sent == 2
    assert nobody == 0
    assert tab_one.sent == tab_two.sent == [{"type": "notification"}]
    assert stranger.sent == []
    assert hub.online_users() == {user, other}
    assert hub.has_user(user)


@pytest.mark.case(id="REALTIME-HUB-002")
async def test_closed_and_broken_connections_leave_the_registry() -> None:
    hub = RealtimeHub()
    user, session = uuid7(), uuid7()
    alive, broken = FakeConnection(), FakeConnection(broken=True)
    hub.register(user, session, alive)
    hub.register(user, uuid7(), broken)

    sent = await hub.send_to_user(user, {"type": "ping"})
    hub.unregister(alive)
    hub.unregister(alive)

    assert sent == 1
    assert not hub.has_user(user)
    assert hub.online_users() == set()


@pytest.mark.case(id="REALTIME-HUB-003")
async def test_closing_a_session_closes_only_its_connections() -> None:
    hub = RealtimeHub()
    user, revoked, kept = uuid7(), uuid7(), uuid7()
    first, second, third = FakeConnection(), FakeConnection(), FakeConnection()
    hub.register(user, revoked, first)
    hub.register(user, revoked, second)
    hub.register(user, kept, third)

    await hub.close_session(revoked, 4401)

    assert (first.closed_with, second.closed_with, third.closed_with) == (4401, 4401, None)
    assert await hub.send_to_user(user, {"type": "ping"}) == 1
    assert third.sent == [{"type": "ping"}]

    await hub.close_all(1001)
    assert third.closed_with == 1001
    assert hub.online_users() == set()


@pytest.mark.case(id="REALTIME-HUB-004")
async def test_broadcast_reaches_everyone() -> None:
    hub = RealtimeHub()
    connections = [FakeConnection() for _ in range(3)]
    for connection in connections:
        hub.register(uuid7(), uuid7(), connection)

    await hub.broadcast({"type": "resync"})

    assert all(connection.sent == [{"type": "resync"}] for connection in connections)
