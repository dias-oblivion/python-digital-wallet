from fastapi import APIRouter

from api.schemas.users import UserResponse
from api.wiring import CurrentUserDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(current_user: CurrentUserDep) -> UserResponse:
    return UserResponse.from_entity(current_user)
