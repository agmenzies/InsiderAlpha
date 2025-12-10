from fastapi import APIRouter, Depends, HTTPException, status, Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.config import Config
from authlib.integrations.starlette_client import OAuth, OAuthError
from app.core.config import settings

router = APIRouter()

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {error.description}")
    
    user = token.get('userinfo')
    if user:
        request.session['user'] = user
        email = user.get('email')
        if email not in settings.ALLOWED_USERS:
             # Even if logged in Google, if not in whitelist, we deny access.
             # We might want to clear session too.
             request.session.pop('user', None)
             raise HTTPException(status_code=403, detail="User not authorized.")
        
        return {"user": user}
    else:
        raise HTTPException(status_code=400, detail="Could not fetch user info.")

@router.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    return {"message": "Logged out"}

# Dependency to check if user is authorized
async def verify_authorized_user(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    email = user.get('email')
    if email not in settings.ALLOWED_USERS:
        raise HTTPException(status_code=403, detail="User not authorized")
    return user
