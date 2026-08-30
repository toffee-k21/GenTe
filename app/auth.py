import os
import uuid
import bcrypt
import jwt

from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Security,
    status,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from pydantic import BaseModel, EmailStr

from boto3.dynamodb.conditions import Key

from botocore.exceptions import ClientError

from app.clients.dynamodb import users_table


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# ============================================================
# Configuration
# ============================================================

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "teaserai-super-secret-teaser-key-change-in-production",
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60",
    )
)

security = HTTPBearer()


# ============================================================
# Schemas
# ============================================================

class UserRegisterSchema(BaseModel):

    email: EmailStr
    password: str


class UserLoginSchema(BaseModel):

    email: EmailStr
    password: str


class TokenSchema(BaseModel):

    access_token: str
    token_type: str = "bearer"
    email: str


# ============================================================
# Password hashing
# ============================================================

def hash_password(
    password: str,
) -> str:

    salt = bcrypt.gensalt()

    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        salt,
    )

    return hashed.decode("utf-8")


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:

    try:

        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    except Exception:

        return False


# ============================================================
# JWT
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: timedelta = None,
) -> str:

    to_encode = data.copy()

    if expires_delta:

        expire = (
            datetime.now(timezone.utc)
            + expires_delta
        )

    else:

        expire = (
            datetime.now(timezone.utc)
            + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def verify_token(
    token: str,
) -> dict:

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


# ============================================================
# Current user
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(
        security
    ),
):

    token = credentials.credentials

    payload = verify_token(token)

    user_id = payload.get("user_id")
    email = payload.get("sub")

    if user_id is None or email is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return {
        "user_id": user_id,
        "email": email,
    }


# ============================================================
# Find user by email
# ============================================================

def get_user_by_email(
    email: str,
):

    response = users_table.query(

        IndexName="email-index",

        KeyConditionExpression=Key(
            "email"
        ).eq(email),

        Limit=1,
    )

    items = response.get(
        "Items",
        []
    )

    if not items:
        return None

    return items[0]


# ============================================================
# Register
# ============================================================

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserRegisterSchema,
):

    email = user_data.email.lower()

    # --------------------------------------------------------
    # Check email using GSI
    # --------------------------------------------------------

    try:

        existing_user = get_user_by_email(
            email
        )

        if existing_user:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered",
            )

    except HTTPException:

        raise

    except ClientError as e:

        print(
            "DynamoDB register error:",
            e.response["Error"]
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during registration",
        )


    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    user_id = str(
        uuid.uuid4()
    )

    hashed_password = hash_password(
        user_data.password
    )

    user = {

        "user_id": user_id,

        "email": email,

        "password": hashed_password,

        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


    # --------------------------------------------------------
    # Save user
    # --------------------------------------------------------

    try:

        users_table.put_item(
            Item=user,

            ConditionExpression=(
                "attribute_not_exists(user_id)"
            ),
        )

    except ClientError as e:

        print(
            "DynamoDB put user error:",
            e.response["Error"]
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during registration",
        )


    return {
        "message": "User registered successfully",
        "user_id": user_id,
    }


# ============================================================
# Login
# ============================================================

@router.post(
    "/login",
    response_model=TokenSchema,
)
async def login(
    user_data: UserLoginSchema,
):

    email = user_data.email.lower()

    # --------------------------------------------------------
    # Find user using email GSI
    # --------------------------------------------------------

    try:

        user = get_user_by_email(
            email
        )

    except ClientError as e:

        print(
            "DynamoDB login error:",
            e.response["Error"]
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during login",
        )


    # --------------------------------------------------------
    # Validate credentials
    # --------------------------------------------------------

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


    if not verify_password(
        user_data.password,
        user["password"],
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    access_token = create_access_token(

        data={

            "sub": user["email"],

            "user_id": user["user_id"],
        }
    )


    return {

        "access_token": access_token,

        "token_type": "bearer",

        "email": user["email"],
    }


# ============================================================
# Me
# ============================================================

@router.get("/me")
async def get_me(
    current_user=Depends(
        get_current_user
    ),
):

    return current_user