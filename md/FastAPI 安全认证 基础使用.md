### FastAPI 安全认证 基础使用

安全认证是一个很复杂的话题

> FastAPI provides several tools to help you deal with Security easily, rapidly, in a standard way, without having to study and learn all the security specifications.
> fastapi 提供了几种很 easy，很快速，基于安全标准的方式的工具解决这些问题，可以使你免去学习了解所有有关安全校验的系统知识

当然现在 Auth2 是主流，expect 我们使用 https，但是没说必须使用

看下官方给的 demo
https://fastapi.tiangolo.com/tutorial/security/first-steps/?h=sec

```python
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}
```

#### 代码分析

`oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")`关键点在于`tokenUrl="token"`,相当于提供了一个 Path

`async def read_items(token: str = Depends(oauth2_scheme)):`使用依赖项`Depends(oauth2_scheme)`,根据之前源码分析，需要先解决依赖才会进入 endpoints，这里会返回依赖结果，看源码是实现了`__call__()`方法的

看看官方另一个正经的 demo

````python
async def get_current_user(token: str = Depends(oauth2_scheme)):
    ```
    token验证逻辑
    ```
    return user

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

````

使用子依赖，对 token 进行处理，得到结果。通常会通过查数据库返回用户的 model。

我们自己的 demo 看看具体流程：

```python
from datetime import datetime, timedelta
from typing import Optional
from starlette import status
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class User(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


USER_LIST = [
    User(username="test", password="test_pw")
]


def get_user(username: str) -> User:
    # 伪数据库
    for user in USER_LIST:
        if user.username == username:
            return user


form_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def create_token(user: User, expires_delta: Optional[timedelta] = None):
    expire = datetime.utcnow() + expires_delta or timedelta(minutes=15)
    return jwt.encode(
        claims={"sub": user.username, "exp": expire},
        key=SECRET_KEY,
        algorithm=ALGORITHM
    )


@app.post("/token")
async def login_get_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user: User = get_user(form_data.username)
    if not user or user.password != form_data.password:
        raise form_exception
    access_token = create_token(user=user, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def token_to_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username, expire = payload.get("sub"), payload.get("exp")
        user = get_user(username)
        if user is None:
            raise JWTError
    except JWTError:
        raise credentials_exception
    return user


@app.get("/items/", response_model=User)
async def read_items(user: User = Depends(token_to_user)):
    return user


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

简单的模拟 demo，它包含了用户登录获取 token，与进行 token 认证两种功能，下面我们将慢慢解释这些内容。

#### 预定义内容

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
```

这里包含了安全认证类，秘钥，算法，过期时间的定义，以及两个验证 model。

#### 模拟数据库

假设通过用户名从数据库中获取 user 的过程

```python
USER_LIST = [
    User(username="test", password="test_pw")
]

def get_user(username: str) -> User:
    # 伪数据库
    for user in USER_LIST:
        if user.username == username:
            return user
```

#### 登录获取 token

```python
form_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def create_token(user: User, expires_delta: Optional[timedelta] = None):
    expire = datetime.utcnow() + expires_delta or timedelta(minutes=15)
    return jwt.encode(
        claims={"sub": user.username, "exp": expire},
        key=SECRET_KEY,
        algorithm=ALGORITHM
    )


@app.post("/token")
async def login_get_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user: User = get_user(form_data.username)
    if not user or user.password != form_data.password:
        raise form_exception
    access_token = create_token(user=user, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}
```

#### 认证 token 获取用户

```python
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def token_to_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username, expire = payload.get("sub"), payload.get("exp")
        user = get_user(username)
        if user is None:
            raise JWTError
    except JWTError:
        raise credentials_exception
    return user


@app.get("/items/", response_model=User)
async def read_items(user: User = Depends(token_to_user)):
    return user
```

测试 curl：

```shell
curl -X 'POST' \
  'http://127.0.0.1:8000/token' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=&username=test&password=test_pw&scope=&client_id=&client_secret='

curl -X 'GET' \
  'http://127.0.0.1:8000/items/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNjQ5ODQwNzU2fQ.yUDeys7Ru2-qtkrSFsNVIdB5RsxhorJ6BbN7UB6g1iw'
```

本章 ok
