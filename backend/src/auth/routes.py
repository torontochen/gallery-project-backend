from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    status,
    BackgroundTasks,
    Response,
    Cookie,
    Request,
)
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.db.redis import add_jti_to_blocklist

from .dependencies import (
    AccessTokenBearer,
    RefreshTokenBearer,
    RoleChecker,
)
from .schemas import (
    ArtistProfileModel,
    UserCreateModel,
    UserLoginModel,
    EmailModel,
    PasswordResetRequestModel,
    PasswordResetConfirmModel,
    ProfileUpdateModel,
    UserModel,
)
from .service import UserService
from .utils import (
    create_access_token,
    verify_password,
    generate_passwd_hash,
    create_url_safe_token,
    decode_url_safe_token,
    decode_token,
)
from src.errors import UserAlreadyExists, UserNotFound, InvalidCredentials, InvalidToken
from src.config import Config
from src.celery_tasks import send_email

auth_router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


REFRESH_TOKEN_EXPIRY = 10


# Bearer Token


@auth_router.post("/send_mail")
async def send_mail(emails: EmailModel):
    emails = emails.addresses

    html = "<h1>Welcome to the app</h1>"
    subject = "Welcome to our app"

    send_email.delay(emails, subject, html)

    return {"message": "Email sent successfully"}


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user_Account(
    user_data: ProfileUpdateModel,
    bg_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Create user account using email, username, first_name, last_name
    params:
        user_data: UserCreateModel
    """
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise UserAlreadyExists()

    new_user = await user_service.create_user(user_data, session)

    token = create_url_safe_token({"email": email})

    link = f"http://{Config.DOMAIN}/api/auth/verify/{token}"

    # html = f"""
    # <h1>Verify your Email</h1>
    # <p>Please click this <a href="{link}">link</a> to verify your email</p>
    # """

    template_name = "auth_confirmation_email.html"
    template_body = {
        "name": new_user.username,
        "verification_link": link,
        "message": "Thank you for registering Monohaus Gallery. Please click to verify your email",
        "function": "Verify Email",
    }

    emails = [email]

    subject = "Verify Your email"

    send_email.delay(emails, subject, template_body, template_name)

    return {
        "message": "Account Created! Check email to verify your account",
        "user": new_user,
    }


@auth_router.get("/check-user/{email}")
async def check_user_exists(email: str, session: AsyncSession = Depends(get_session)):
    user_exists = await user_service.user_exists(email, session)

    return JSONResponse(content={"exists": user_exists})


@auth_router.get("/verify/{token}")
async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):

    token_data = decode_url_safe_token(token)

    user_email = token_data.get("email")

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)

        if not user:
            raise UserNotFound()

        await user_service.update_user(user, {"is_verified": True}, session)

        # return JSONResponse(
        #     content={"message": "Account verified successfully"},
        #     status_code=status.HTTP_200_OK,
        # )
        return RedirectResponse(
            url="http://localhost:5173/auth", status_code=status.HTTP_303_SEE_OTHER
        )

    return JSONResponse(
        content={"message": "Error occured during verification"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@auth_router.get("/")
async def get_all_artists(
    session: AsyncSession = Depends(get_session), response_model=ArtistProfileModel
):
    artists = await user_service.get_all_artists(session)
    return artists


@auth_router.post("/update-profile")
async def update_user_profile(
    user_data: ProfileUpdateModel,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(AccessTokenBearer()),
    response_model=UserModel,
):
    # print("Profile update data:", user_data)
    # print("Received profile update request for user:", token_details)
    user = await user_service.get_user_by_email(token_details["user"]["email"], session)
    if not user:
        raise UserNotFound()
    user_data_dict = user_data.model_dump(exclude_unset=True)
    # print("User data dict after excluding unset fields:", user_data_dict)
    user_data_dict["hashed_password"] = (
        generate_passwd_hash(user_data_dict["password"])
        if user_data_dict["password"] != "None"
        else user.hashed_password
    )
    user_data_dict.pop("password", None)  # Remove the plain password from the dict
    if user_data_dict["first_name"] is not None:
        user_data_dict["username"] = user_data_dict["first_name"]

    updated_user = await user_service.update_user(user, user_data_dict, session)

    # return JSONResponse(content={"message": "Profile Updated Successfully", "user": updated_user})
    return updated_user


@auth_router.post("/login")
async def login_users(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    # print("Login Attempt:", login_data)
    email = login_data.email
    password = login_data.password
    isTrustedDevice = login_data.isTrustedDevice

    user = await user_service.get_user_by_email(email, session)
    if user.shopping_cart:
        shopping_cart = user.shopping_cart.model_dump()
        # print("user shopping cart", shopping_cart)
        shopping_cart["user_id"] = str(shopping_cart["user_id"])
        shopping_cart["uid"] = str(shopping_cart["uid"])
        shopping_cart["added_date"] = str(shopping_cart["added_date"])
        for index, item in enumerate(shopping_cart["arts"]):
            shopping_cart["arts"][index]["art_id"] = str(item["art_id"])
            shopping_cart["arts"][index]["added_at"] = str(item["added_at"])

    if user is not None:
        password_valid = verify_password(password, user.hashed_password)

        if password_valid:
            access_token = create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                }
            )

            refresh_token = create_access_token(
                user_data={"email": user.email, "user_uid": str(user.uid)},
                refresh=True,
                expiry=timedelta(days=REFRESH_TOKEN_EXPIRY),
            )

            response = JSONResponse(
                content={
                    "message": "Login successful",
                    "access_token": access_token,
                    # "refresh_token": refresh_token if isTrustedDevice else None,
                    "user": {
                        "uid": str(user.uid),
                        "email": user.email,
                        "first_name": user.first_name,
                        "username": user.username,
                        "last_name": user.last_name,
                        "is_verified": user.is_verified,
                        "role": user.role,
                        "bio": user.bio,
                        "country": user.country,
                        "address": user.address,
                        "delivery_address": user.delivery_address,
                        "phone_number": user.phone_number,
                        "shopping_cart": shopping_cart if user.shopping_cart else None,
                    },
                }
            )

            if isTrustedDevice:
                response.set_cookie(
                    key="refresh_token",
                    value=refresh_token,
                    httponly=True,  # Prevents JavaScript access (XSS protection)
                    samesite="lax",  # Blocks the cookie on cross-site requests (CSRF protection)
                    secure=False,  # Only sends the cookie over HTTPS
                    max_age=600000,  # Expiration in seconds (e.g., 7 days)
                    path="http://localhost:8000/api/auth/refresh_token",  # Recommended: restrict cookie to the refresh endpoint
                )

            return response

    # raise InvalidCredentials()
    raise HTTPException(
        detail="Invalid Email Or Password !", status_code=status.HTTP_400_BAD_REQUEST
    )


@auth_router.post("/refresh_token")
# async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
# async def get_new_access_token(refresh_token: Annotated[str | None, Cookie()] = None):
# async def get_new_access_token(refresh_token: Optional[str] = Cookie(None)):
async def get_new_access_token(
    request: Request, session: AsyncSession = Depends(get_session)
):
    refresh_token = request.cookies.get("refresh_token")
    # print("Refresh Token Request Received. Refresh Token:", refresh_token)
    if not refresh_token:
        return {"error": "Refresh token missing"}
    token_details = decode_token(refresh_token)
    expiry_timestamp = token_details["exp"]

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        # print("token details", token_details)
        new_access_token = create_access_token(user_data=token_details["user"])
        email = token_details["user"]["email"]
        user = await user_service.get_user_by_email(email, session)

        if user.shopping_cart:
            shopping_cart = user.shopping_cart.model_dump()
            # print("user shopping cart", shopping_cart)
            shopping_cart["user_id"] = str(shopping_cart["user_id"])
            shopping_cart["added_date"] = str(shopping_cart["added_date"])
            shopping_cart["uid"] = str(shopping_cart["uid"])

            for index, item in enumerate(shopping_cart["arts"]):
                shopping_cart["arts"][index]["art_id"] = str(item["art_id"])
                shopping_cart["arts"][index]["added_at"] = str(item["added_at"])

        return JSONResponse(
            content={
                "access_token": new_access_token,
                "user": {
                    "uid": str(user.uid),
                    "email": user.email,
                    "first_name": user.first_name,
                    "username": user.username,
                    "last_name": user.last_name,
                    "is_verified": user.is_verified,
                    "role": user.role,
                    "bio": user.bio,
                    "country": user.country,
                    "address": user.address,
                    "delivery_address": user.delivery_address,
                    "phone_number": user.phone_number,
                    "avatar_url": user.avatar_url,
                    "shopping_cart": shopping_cart if user.shopping_cart else None,
                },
            }
        )

    raise InvalidToken()


# @auth_router.get("/me", response_model=UserBooksModel)
# async def get_current_user(
#     user=Depends(get_current_user), _: bool = Depends(role_checker)
# ):
#     return user


@auth_router.post("/logout")
async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):

    # print("Logout Request Received. Token Details:", token_details)
    jti = token_details["jti"]
    # print("Revoking token with JTI:", jti)

    await add_jti_to_blocklist(jti)

    response = JSONResponse(
        content={"message": "Logged Out Successfully"}, status_code=status.HTTP_200_OK
    )

    response.delete_cookie(
        key="refresh_token",
        path="http://localhost:8000/api/auth/refresh_token",  # Must match the original path
        httponly=True,  # Security best practice
        samesite="lax",  # Or 'strict' based on your original settings
        secure=False,  # Recommended for production HTTPS
    )

    return response


@auth_router.post("/password-reset-request")
async def password_reset_request(email_data: PasswordResetRequestModel):
    email = email_data.email

    token = create_url_safe_token({"email": email})

    # link = f"http://{Config.DOMAIN}/api/auth/password-reset-confirm/{token}"
    link = f"http://localhost:5173/reset-password/{token}"

    # html_message = f"""
    # <h1>Reset Your Password</h1>
    # <p>Please click this <a href="{link}">link</a> to Reset Your Password</p>
    # """

    template_name = "auth_confirmation_email.html"
    template_body = {
        "name": email,
        "verification_link": link,
        "message": "Thank you for choosing Monohaus Gallery. Please click to reset your password",
        "function": "Reset Password",
    }

    emails = [email]

    subject = "Reset Your Password"

    # send_email.delay([email], subject, html_message)
    send_email.delay(emails, subject, template_body, template_name)

    # return RedirectResponse(
    #         url="http://localhost:5173/reset-password",
    #         status_code=status.HTTP_303_SEE_OTHER
    #      )

    return JSONResponse(
        content={
            "message": "Please check your email for instructions to reset your password",
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/password-reset-confirm/{token}")
async def reset_account_password(
    token: str,
    passwords: PasswordResetConfirmModel,
    session: AsyncSession = Depends(get_session),
):
    # print("Password reset confirmation received. Token:", token)
    # print("New password data:", passwords)
    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password

    if new_password != confirm_password:
        raise HTTPException(
            detail="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST
        )

    token_data = decode_url_safe_token(token)

    user_email = token_data.get("email")

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)

        if not user:
            raise UserNotFound()

        passwd_hash = generate_passwd_hash(new_password)
        await user_service.update_user(user, {"hashed_password": passwd_hash}, session)

        return JSONResponse(
            content={"message": "Password reset Successfully"},
            status_code=status.HTTP_200_OK,
        )

    return JSONResponse(
        content={"message": "Error occured during password reset."},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
