import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import hash_password
from app.models import Role, TrainingAssignment, User, UserProgress
from app.schemas.users import UserCreate, UserResponse, UserSummary, UserUpdate
from app.storage import (
    ObjectNotFoundError,
    ObjectStorage,
    StorageError,
    StoredObject,
    get_object_storage,
)

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_AVATAR_FORMATS = {"JPEG", "PNG", "WEBP"}
AVATAR_EDGE_PIXELS = 512
Image.MAX_IMAGE_PIXELS = 20_000_000


class UserService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self._session = session
        self._storage = storage or get_object_storage()

    @staticmethod
    def _normalize_avatar(data: bytes) -> bytes:
        try:
            with Image.open(BytesIO(data)) as source:
                source.verify()
                image_format = source.format
            if image_format not in ALLOWED_AVATAR_FORMATS:
                raise ValueError("Unsupported avatar format.")
            with Image.open(BytesIO(data)) as source:
                if source.width > 4096 or source.height > 4096:
                    raise ValueError("Avatar dimensions are too large.")
                normalized = ImageOps.exif_transpose(source)
                normalized.thumbnail(
                    (AVATAR_EDGE_PIXELS, AVATAR_EDGE_PIXELS),
                    Image.Resampling.LANCZOS,
                )
                if normalized.mode not in {"RGB", "RGBA"}:
                    normalized = normalized.convert(
                        "RGBA" if "transparency" in source.info else "RGB"
                    )
                output = BytesIO()
                normalized.save(output, format="WEBP", quality=86, method=6)
                return output.getvalue()
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
            raise AppError(
                code="INVALID_AVATAR",
                message="The uploaded file is not a valid profile image.",
                status_code=415,
            ) from exc

    async def _employee(self, *, company_id, user_id) -> User:
        user = await self._session.scalar(
            select(User).where(
                User.id == user_id,
                User.company_id == company_id,
                User.role == Role.EMPLOYEE,
            )
        )
        if user is None:
            raise AppError(
                code="USER_NOT_FOUND",
                message="The employee was not found.",
                status_code=404,
            )
        return user

    async def create_employee(self, *, company_id, payload: UserCreate) -> User:
        email = str(payload.email).lower()
        if await self._session.scalar(select(User.id).where(User.email == email)):
            raise AppError(
                code="EMAIL_ALREADY_EXISTS",
                message="This email is already in use.",
                status_code=409,
            )
        if await self._session.scalar(
            select(User.id).where(User.company_id == company_id, User.cpf == payload.cpf)
        ):
            raise AppError(
                code="CPF_ALREADY_EXISTS",
                message="This CPF is already in use by the company.",
                status_code=409,
            )
        user = User(
            company_id=company_id,
            email=email,
            full_name=payload.full_name.strip(),
            cpf=payload.cpf,
            password_hash=hash_password(payload.password),
            role=Role.EMPLOYEE,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def list_employees(self, *, company_id) -> list[UserSummary]:
        rows = (
            await self._session.execute(
                select(
                    User,
                    func.count(TrainingAssignment.id.distinct()).label("assigned"),
                    func.count(UserProgress.id.distinct())
                    .filter(UserProgress.progress_percent == 100)
                    .label("completed"),
                )
                .outerjoin(
                    TrainingAssignment,
                    (TrainingAssignment.employee_id == User.id)
                    & (TrainingAssignment.company_id == company_id),
                )
                .outerjoin(
                    UserProgress,
                    (UserProgress.user_id == User.id) & (UserProgress.company_id == company_id),
                )
                .where(User.company_id == company_id, User.role == Role.EMPLOYEE)
                .group_by(User.id)
                .order_by(User.full_name)
            )
        ).all()
        result: list[UserSummary] = []
        for user, assigned, completed in rows:
            assigned_count = int(assigned)
            completed_count = min(int(completed), assigned_count)
            result.append(
                UserSummary(
                    **UserResponse.model_validate(user).model_dump(),
                    assigned=assigned_count,
                    completed=completed_count,
                    pending=max(assigned_count - completed_count, 0),
                    completion_percent=(
                        round(completed_count / assigned_count * 100) if assigned_count else 0
                    ),
                )
            )
        return result

    async def update_employee(self, *, company_id, user_id, payload: UserUpdate) -> User:
        user = await self._employee(company_id=company_id, user_id=user_id)

        if payload.email is not None:
            email = str(payload.email).lower()
            duplicate = await self._session.scalar(
                select(User.id).where(User.email == email, User.id != user.id)
            )
            if duplicate:
                raise AppError(
                    code="EMAIL_ALREADY_EXISTS",
                    message="This email is already in use.",
                    status_code=409,
                )
            user.email = email
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.cpf is not None:
            duplicate_cpf = await self._session.scalar(
                select(User.id).where(
                    User.company_id == company_id,
                    User.cpf == payload.cpf,
                    User.id != user.id,
                )
            )
            if duplicate_cpf:
                raise AppError(
                    code="CPF_ALREADY_EXISTS",
                    message="This CPF is already in use by the company.",
                    status_code=409,
                )
            user.cpf = payload.cpf
        if payload.is_active is not None:
            user.is_active = payload.is_active

        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def upload_avatar(self, *, company_id, user_id, upload: UploadFile) -> User:
        user = await self._employee(company_id=company_id, user_id=user_id)
        if upload.content_type not in ALLOWED_AVATAR_TYPES:
            raise AppError(
                code="INVALID_AVATAR",
                message="Only JPG, PNG, and WebP profile images are accepted.",
                status_code=415,
            )

        from app.core.config import get_settings

        maximum_bytes = get_settings().max_avatar_size_mb * 1024 * 1024
        data = await upload.read(maximum_bytes + 1)
        if len(data) > maximum_bytes:
            raise AppError(
                code="FILE_TOO_LARGE",
                message="The profile image exceeds the upload limit.",
                status_code=413,
            )
        normalized = await asyncio.to_thread(self._normalize_avatar, data)
        object_key = f"companies/{company_id}/avatars/{user.id}/{uuid4()}.webp"
        previous_key = user.avatar_object_key
        try:
            await self._storage.put(object_key, normalized, content_type="image/webp")
        except StorageError as exc:
            raise AppError(
                code="STORAGE_UNAVAILABLE",
                message="The profile image service is temporarily unavailable.",
                status_code=503,
            ) from exc

        user.avatar_object_key = object_key
        user.avatar_content_type = "image/webp"
        user.avatar_updated_at = datetime.now(UTC)
        try:
            await self._session.commit()
            await self._session.refresh(user)
        except Exception:
            await self._session.rollback()
            with suppress(StorageError):
                await self._storage.delete(object_key)
            raise
        if previous_key and previous_key != object_key:
            with suppress(StorageError):
                await self._storage.delete(previous_key)
        return user

    async def get_avatar(self, *, company_id, user_id) -> StoredObject:
        user = await self._session.scalar(
            select(User).where(User.id == user_id, User.company_id == company_id)
        )
        if user is None or user.avatar_object_key is None:
            raise AppError(
                code="AVATAR_NOT_FOUND",
                message="Profile image not found.",
                status_code=404,
            )
        try:
            return await self._storage.get(user.avatar_object_key)
        except ObjectNotFoundError as exc:
            raise AppError(
                code="AVATAR_NOT_FOUND",
                message="Profile image not found.",
                status_code=404,
            ) from exc
        except StorageError as exc:
            raise AppError(
                code="STORAGE_UNAVAILABLE",
                message="The profile image service is temporarily unavailable.",
                status_code=503,
            ) from exc

    async def delete_avatar(self, *, company_id, user_id) -> User:
        user = await self._employee(company_id=company_id, user_id=user_id)
        object_key = user.avatar_object_key
        user.avatar_object_key = None
        user.avatar_content_type = None
        user.avatar_updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(user)
        if object_key:
            with suppress(StorageError):
                await self._storage.delete(object_key)
        return user
