from dishka import AsyncContainer
from starlette.requests import Request


async def resolve[T](request: Request, dependency: type[T]) -> T:
    """Достаёт зависимость из request-контейнера dishka.

    Аналог `FromDishka` для sqladmin: его вьюшки и backend входа — не FastAPI-роуты,
    поэтому внедрение через сигнатуру им недоступно. Вызывается только на HTTP-границе
    админки, внутрь сервисов контейнер не передаётся.
    """
    container: AsyncContainer = request.state.dishka_container
    return await container.get(dependency)
