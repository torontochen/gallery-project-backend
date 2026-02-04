from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import AccessTokenBearer, RoleChecker
from src.arts.service import ArtService
from src.db.main import get_session

from .schemas import ArtModel, ArtUpdateModel, ArtCreateModel
from src.errors import ArtNotFound, ArtistNotFound

art_router = APIRouter()
art_service = ArtService()
acccess_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(["admin", "user", "artist"]))

@art_router.get("/{artist_id}", response_model=List[ArtModel], dependencies=[role_checker])
async def get_arts_by_artist(
    artist_id: str,
    session: AsyncSession = Depends(get_session),
):
    arts = await art_service.get_arts_by_artist(artist_id, session)
    if arts is None:
        raise ArtistNotFound()
    else:
        return arts

@art_router.get("/{art_uid}", response_model=ArtModel, dependencies=[role_checker])
async def get_art_by_id(
    art_uid: str,
    session: AsyncSession = Depends(get_session),
):
    art = await art_service.get_art_by_id(art_uid, session)
    if art is None:
        raise ArtNotFound()
    else:
        return art

# @art_router.post("/", response_model=ArtModel, status_code=status.HTTP_201_CREATED, dependencies=[role_checker])
@art_router.post("/", response_model=ArtModel, status_code=status.HTTP_201_CREATED)
async def create_art(
    art_create_data: ArtCreateModel,
    session: AsyncSession = Depends(get_session),
):
    new_art = await art_service.create_art(art_create_data, session)
    return new_art

@art_router.put("/{art_uid}", response_model=ArtModel, dependencies=[role_checker])
async def update_art(
    art_uid: str,
    update_data: ArtUpdateModel,
    session: AsyncSession = Depends(get_session),
):
    updated_art = await art_service.update_art(art_uid, update_data, session)
    if updated_art is None:
        raise ArtNotFound()
    else:
        return updated_art