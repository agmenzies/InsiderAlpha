from fastapi import FastAPI, Depends
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings
from app.core.auth import router as auth_router, verify_authorized_user

app = FastAPI(title="Insider-Alpha")

# Add Session Middleware for Authlib
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
from app.api.insider import router as insider_router
app.include_router(insider_router, prefix="/api", tags=["insider"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Insider-Alpha"}

@app.get("/protected", dependencies=[Depends(verify_authorized_user)])
def protected_route():
    return {"message": "You are authorized!"}
