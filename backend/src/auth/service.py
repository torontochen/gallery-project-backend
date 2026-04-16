from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import User

from .schemas import UserCreateModel
from .utils import generate_passwd_hash


class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)

        result = await session.exec(statement)

        user = result.first()
        # print(f"Queried user by email: {email}, found: {user}")

        return user

    async def get_all_artists(self, session: AsyncSession):
        statement = select(User).where(User.role == "artist")

        result = await session.exec(statement)

        artists = result.all()

        return artists

    async def user_exists(self, email, session: AsyncSession):
        user = await self.get_user_by_email(email, session)

        return True if user is not None else False

    async def create_user(self, user_data: UserCreateModel, session: AsyncSession):
        user_data_dict = user_data.model_dump()

        new_user = User(**user_data_dict)
        index_e = user_data_dict["email"].index("@")
        index_dot = user_data_dict["email"].index(".")
        username = user_data_dict["email"][:index_e] + user_data_dict["email"][index_e + 1:index_dot]
        new_user.username = username
        new_user.hashed_password = generate_passwd_hash(user_data_dict["password"])
        # new_user.role = "user"
        # print(new_user)

        session.add(new_user)

        await session.commit()

        return new_user


    async def update_user(self, user:User , user_data: dict, session:AsyncSession):

        for k, v in user_data.items():
            setattr(user, k, v)
       

        await session.commit()

        return user