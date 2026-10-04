from uuid import UUID, uuid7

from src.api.exc.profile import (
    AvatarNotImageError,
    AvatarNotUploadedError,
    AvatarTooLargeError,
    ForeignAvatarKeyError,
)
from src.api.profile.dto import Affiliation, Profile
from src.api.profile.enums import AvatarContentType
from src.core.db.models.user import User
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.s3.dto import PresignedUpload
from src.core.s3.exc import S3FileTooLargeError, S3ObjectNotFoundError
from src.core.s3.service import S3Storage
from src.core.security.dto import CurrentUser


class ProfileService:
    """Профиль: ФИО, группа или кафедра, почта и аватарка из S3."""

    def __init__(self, uow: UnitOfWork, storage: S3Storage) -> None:
        self._uow = uow
        self._storage = storage

    async def get_profile(self, user: CurrentUser) -> Profile:
        return await self._to_dto(await self._get_user(user.user_id))

    async def start_avatar_upload(
        self, user: CurrentUser, content_type: str, file_size: int
    ) -> PresignedUpload:
        """Выдаёт форму прямой загрузки картинки в S3.

        Raises:
            AvatarNotImageError: тип файла не PNG, JPEG, WebP или GIF.
            AvatarTooLargeError: файл больше лимита.
        """
        self._check_image(content_type)
        self._check_size(file_size)
        return await self._storage.presign_upload(
            f"{self._key_prefix(user.user_id)}{uuid7()}", content_type
        )

    async def set_avatar(self, user: CurrentUser, key: str) -> Profile:
        """Ставит загруженную картинку аватаркой; прежняя удаляется из S3.

        Замена фиксируется только после удаления прежнего файла: если S3 не ответил,
        остаётся прежняя аватарка.

        Raises:
            ForeignAvatarKeyError: ключ выдан не для аватарки этого пользователя.
            AvatarNotUploadedError: файла в S3 нет.
            AvatarNotImageError: загружена не PNG, JPEG, WebP или GIF.
            AvatarTooLargeError: файл больше лимита.
            S3UnavailableError, S3TimeoutError, S3BadResponseError: прежний файл удалить
                не удалось.
        """
        if not key.startswith(self._key_prefix(user.user_id)):
            raise ForeignAvatarKeyError
        try:
            stored = await self._storage.stat(key)
        except S3ObjectNotFoundError as exc:
            raise AvatarNotUploadedError from exc
        self._check_image(stored.content_type)
        self._check_size(stored.size)

        account = await self._get_user(user.user_id)
        previous_key = account.avatar_key
        account.avatar_key = key
        await self._uow.flush()
        if previous_key is not None and previous_key != key:
            await self._storage.delete(previous_key)
        await self._uow.commit()
        return await self._to_dto(account)

    async def remove_avatar(self, user: CurrentUser) -> Profile:
        """Убирает аватарку вместе с файлом в S3.

        Raises:
            S3UnavailableError, S3TimeoutError, S3BadResponseError: файл удалить не удалось,
                аватарка остаётся.
        """
        account = await self._get_user(user.user_id)
        previous_key = account.avatar_key
        account.avatar_key = None
        await self._uow.flush()
        if previous_key is not None:
            await self._storage.delete(previous_key)
        await self._uow.commit()
        return await self._to_dto(account)

    async def _get_user(self, user_id: UUID) -> User:
        account = await self._uow.users.get_with_affiliation(user_id)
        if account is None:
            raise InternalError({"user_id": str(user_id)})
        return account

    async def _to_dto(self, account: User) -> Profile:
        return Profile(
            id=account.id,
            last_name=account.last_name,
            first_name=account.first_name,
            middle_name=account.middle_name,
            email=account.email,
            role=account.role,
            group=Affiliation(id=account.group.id, name=account.group.name)
            if account.group
            else None,
            department=Affiliation(id=account.department.id, name=account.department.name)
            if account.department
            else None,
            avatar_url=await self._storage.presign_view(account.avatar_key)
            if account.avatar_key
            else None,
        )

    def _check_size(self, file_size: int) -> None:
        try:
            self._storage.check_size(file_size)
        except S3FileTooLargeError as exc:
            raise AvatarTooLargeError(exc.context) from exc

    @staticmethod
    def _check_image(content_type: str) -> None:
        if content_type.lower() not in AvatarContentType:
            raise AvatarNotImageError({"content_type": content_type})

    @staticmethod
    def _key_prefix(user_id: UUID) -> str:
        return f"users/{user_id}/avatar/"
