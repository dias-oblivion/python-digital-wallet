from fastapi import APIRouter

from wallet.api.schemas.users import UserResponse
from wallet.api.wiring import CurrentUserDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(current_user: CurrentUserDep) -> UserResponse:
    return UserResponse.from_entity(current_user)
