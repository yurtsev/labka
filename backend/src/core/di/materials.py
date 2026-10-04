from dishka import Provider, Scope, provide

from src.api.materials.service import MaterialService


class MaterialsProvider(Provider):
    material_service = provide(MaterialService, scope=Scope.REQUEST)
