from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import AccessTokenBearer, RoleChecker

from src.arts.schemas import ArtModel, ArtUpdateModel, ArtCreateModel
from src.db.models import Art

class ArtService:
    async def get_arts_by_artist(self, artist_id: str, session: AsyncSession):
        statement = select(Art).where(Art.artist_id == artist_id).order_by(desc(Art.creation_date))
        result = await session.exec(statement)
        arts = result.all()
        return arts

    async def get_art_by_id(self, art_uid: str, session: AsyncSession):
        print("art uid received is", art_uid)
        statement = select(Art).where(Art.uid == art_uid)
        result = await session.exec(statement)
        art = result.first()
        print("art found is", art)
        # session.add(new_work)
        # await session.commit()
        # await session.refresh(new_work)
        return art if art is not None else None

    async def create_art(self, art_data: ArtCreateModel, session: AsyncSession):
        art_data_dict = art_data.model_dump()
        new_art = Art(**art_data_dict)
        session.add(new_art)
        await session.commit()
        await session.refresh(new_art)
        return new_art

    async def update_art(self, art_uid: str, update_data: ArtUpdateModel, session: AsyncSession):
        art_to_update = await self.get_art_by_id(art_uid, session)
        if art_to_update is not None:
            update_data_dict = update_data.model_dump()
            for k, v in update_data_dict.items():
                setattr(art_to_update, k, v)
            await session.commit()
            return art_to_update
        else:
            return None