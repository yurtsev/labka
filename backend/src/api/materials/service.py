from collections.abc import Sequence
from uuid import UUID, uuid7

from src.api.exc.materials import (
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    FileAlreadyAttachedError,
    FileNotUploadedError,
    FileTooLargeError,
    ForeignFileKeyError,
    MaterialFileNotFoundError,
    MaterialNotFoundError,
)
from src.api.materials.dto import Material, MaterialFields, MaterialFile, UploadedFile
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.dto.page import Page, PageRequest
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.course import Course
from src.core.db.models.course_material import CourseMaterial
from src.core.db.models.course_material_file import CourseMaterialFile
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.s3.dto import PresignedUpload
from src.core.s3.exc import S3FileTooLargeError, S3ObjectNotFoundError
from src.core.s3.service import S3Storage
from src.core.security.dto import CurrentUser


class MaterialService:
    """Материалы курса: название, текст и файлы. Файлы лежат в S3, в БД — ключ и метаданные."""

    def __init__(self, uow: UnitOfWork, access: AccessService, storage: S3Storage) -> None:
        self._uow = uow
        self._access = access
        self._storage = storage

    async def list_materials(
        self, user: CurrentUser, course_id: UUID, page: PageRequest
    ) -> Page[Material]:
        """Материалы курса, новые первыми, с файлами и ссылками на скачивание.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
        """
        await self._readable(user, course_id)
        materials = await self._uow.course_materials.page_for_course(course_id, page)
        return materials.map(tuple([await self._to_dto(item) for item in materials.items]))

    async def start_upload(
        self, user: CurrentUser, course_id: UUID, content_type: str, file_size: int
    ) -> PresignedUpload:
        """Выдаёт форму прямой загрузки файла в S3.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            FileTooLargeError: файл больше лимита.
        """
        await self._editable(user, course_id)
        self._check_size(file_size)
        return await self._storage.presign_upload(
            f"{self._key_prefix(course_id)}{uuid7()}", content_type
        )

    async def create_material(
        self,
        user: CurrentUser,
        course_id: UUID,
        fields: MaterialFields,
        files: Sequence[UploadedFile],
    ) -> Material:
        """Создаёт материал с файлами, которые браузер уже загрузил в S3.

        Размер и тип файлов берутся из S3, а не из запроса.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            ForeignFileKeyError: ключ выдан не для материалов этого курса.
            FileNotUploadedError: файла в S3 нет.
            FileTooLargeError: файл больше лимита.
            FileAlreadyAttachedError: файл уже прикреплён.
        """
        await self._editable(user, course_id)
        material = CourseMaterial(
            id=uuid7(),
            course_id=course_id,
            title=fields.title,
            text=fields.text,
            files=[await self._stored_file(course_id, file) for file in files],
        )
        self._uow.course_materials.add(material)
        await self._commit_files()
        return await self._reload(material.id)

    async def update_material(
        self, user: CurrentUser, course_id: UUID, material_id: UUID, fields: MaterialFields
    ) -> Material:
        """Меняет название и текст материала.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            MaterialNotFoundError: материала нет в этом курсе.
        """
        await self._editable(user, course_id)
        material = await self._get_material(course_id, material_id)
        material.title = fields.title
        material.text = fields.text
        await self._uow.commit()
        return await self._reload(material.id)

    async def add_file(
        self, user: CurrentUser, course_id: UUID, material_id: UUID, file: UploadedFile
    ) -> Material:
        """Прикрепляет к материалу файл, который браузер уже загрузил в S3; материал
        считается изменённым.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            MaterialNotFoundError: материала нет в этом курсе.
            ForeignFileKeyError: ключ выдан не для материалов этого курса.
            FileNotUploadedError: файла в S3 нет.
            FileTooLargeError: файл больше лимита.
            FileAlreadyAttachedError: файл уже прикреплён.
        """
        await self._editable(user, course_id)
        material = await self._get_material(course_id, material_id)
        stored = await self._stored_file(course_id, file)
        stored.material_id = material.id
        self._uow.course_material_files.add(stored)
        await self._uow.course_materials.touch(material.id)
        await self._commit_files()
        return await self._reload(material.id)

    async def delete_file(
        self, user: CurrentUser, course_id: UUID, material_id: UUID, file_id: UUID
    ) -> None:
        """Убирает файл из материала и из S3; материал считается изменённым.

        Удаление записи фиксируется только после удаления файла: если S3 не ответил,
        транзакция откатывается и файл остаётся в материале.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            MaterialNotFoundError: материала нет в этом курсе.
            MaterialFileNotFoundError: файла нет в этом материале.
            S3UnavailableError, S3TimeoutError, S3BadResponseError: файл удалить не удалось.
        """
        await self._editable(user, course_id)
        material = await self._get_material(course_id, material_id)
        file = await self._uow.course_material_files.get_by_id(file_id)
        if file is None or file.material_id != material.id:
            raise MaterialFileNotFoundError({"file_id": str(file_id)})
        await self._uow.course_material_files.delete(file)
        await self._uow.course_materials.touch(material.id)
        await self._uow.flush()
        await self._storage.delete(file.file_key)
        await self._uow.commit()

    async def delete_material(self, user: CurrentUser, course_id: UUID, material_id: UUID) -> None:
        """Удаляет материал вместе со всеми его файлами в S3.

        Удаление записей фиксируется только после удаления файлов: если S3 не ответил,
        транзакция откатывается и материал остаётся.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            MaterialNotFoundError: материала нет в этом курсе.
            S3UnavailableError, S3TimeoutError, S3BadResponseError: файлы удалить не удалось.
        """
        await self._editable(user, course_id)
        material = await self._get_material(course_id, material_id)
        keys = [file.file_key for file in material.files]
        await self._uow.course_materials.delete(material)
        await self._uow.flush()
        await self._storage.delete_many(keys)
        await self._uow.commit()

    async def _stored_file(self, course_id: UUID, file: UploadedFile) -> CourseMaterialFile:
        """Запись о файле материала по данным из S3; к материалу её привязывает вызывающий."""
        if not file.key.startswith(self._key_prefix(course_id)):
            raise ForeignFileKeyError({"course_id": str(course_id)})
        try:
            stored = await self._storage.stat(file.key)
        except S3ObjectNotFoundError as exc:
            raise FileNotUploadedError({"course_id": str(course_id)}) from exc
        self._check_size(stored.size)
        return CourseMaterialFile(
            id=uuid7(),
            file_key=file.key,
            file_name=file.file_name,
            file_size=stored.size,
            content_type=stored.content_type,
        )

    async def _commit_files(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_course_material_files_file_key":
                raise FileAlreadyAttachedError from exc
            raise

    async def _get_material(self, course_id: UUID, material_id: UUID) -> CourseMaterial:
        material = await self._uow.course_materials.get_with_files(material_id)
        if material is None or material.course_id != course_id:
            raise MaterialNotFoundError({"material_id": str(material_id)})
        return material

    async def _reload(self, material_id: UUID) -> Material:
        material = await self._uow.course_materials.get_with_files(material_id)
        if material is None:
            raise InternalError({"material_id": str(material_id)})
        return await self._to_dto(material)

    async def _to_dto(self, material: CourseMaterial) -> Material:
        return Material(
            id=material.id,
            title=material.title,
            text=material.text,
            created_at=material.created_at,
            updated_at=material.updated_at,
            files=tuple(
                [
                    MaterialFile(
                        id=file.id,
                        file_name=file.file_name,
                        file_size=file.file_size,
                        content_type=file.content_type,
                        download_url=await self._storage.presign_download(
                            file.file_key, file.file_name
                        ),
                    )
                    for file in material.files
                ]
            ),
        )

    async def _readable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.readable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc

    async def _editable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.editable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc
        except access_exc.CourseArchivedError as exc:
            raise CourseArchivedError({"course_id": str(course_id)}) from exc

    @staticmethod
    def _key_prefix(course_id: UUID) -> str:
        return f"courses/{course_id}/materials/"

    def _check_size(self, file_size: int) -> None:
        try:
            self._storage.check_size(file_size)
        except S3FileTooLargeError as exc:
            raise FileTooLargeError(exc.context) from exc
