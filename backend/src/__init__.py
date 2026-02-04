from fastapi import FastAPI
from src.auth.routes import auth_router
from src.arts.routes import art_router
from src.shopping_cart.routes import shopping_cart_router
# from src.tags.routes import tags_router
# from .errors import register_all_errors
# from .middleware import register_middleware


version = "v1"

description = """
A REST API for a book review web service.

This REST API is able to;
- Create Read Update And delete books
- Add reviews to books
- Add tags to Books e.t.c.
    """

version_prefix =f"/api"

app = FastAPI(
    title="Gallery",
    description=description,
    version=version,
    license_info={"name": "MIT License", "url": "https://opensource.org/license/mit"},
    contact={
        "name": "Jack Chen",
        # "url": "https://github.com/jod35",
        "email": "chenhaoyujc@gmail.com",
    },
    # terms_of_service="httpS://example.com/tos",
    # openapi_url=f"{version_prefix}/openapi.json",
    # docs_url=f"{version_prefix}/docs",
    # redoc_url=f"{version_prefix}/redoc"
)

# register_all_errors(app)

# register_middleware(app)


app.include_router(art_router, prefix=f"{version_prefix}/arts", tags=["arts"])
app.include_router(auth_router, prefix=f"{version_prefix}/auth", tags=["auth"])
app.include_router(shopping_cart_router, prefix=f"{version_prefix}/shoppingcart", tags=["shoppingcart"])
# app.include_router(tags_router, prefix=f"{version_prefix}/tags", tags=["tags"])