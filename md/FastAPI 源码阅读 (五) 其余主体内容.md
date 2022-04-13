### FastAPI 源码阅读 (五) 其余主体内容

### params.py 梳理

```python
class ParamTypes(Enum):


class Param(FieldInfo):


class Path(Param):


class Query(Param):


class Header(Param):


class Cookie(Param):


class Body(FieldInfo):


class Form(Body):


class File(Form):


class Depends:


class Security(Depends):


```

以上用法比较简单，按照官方文档即可，可以知道他们基本都是继承类进行生成的，使用了工厂模式进行派生，可以看看他们的工厂函数模式：

### param_functions.py 工厂

单独看 Param 分析：

```python
def Path(  # noqa: N802
    default: Any,
    *,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
    example: Any = Undefined,
    examples: Optional[Dict[str, Any]] = None,
    deprecated: Optional[bool] = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    return params.Path(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        **extra,
    )
```

就是一个函数进行实例化进行返回，比较简单

- utils.py 工具类

  - 这部分在之前的源码中使用，大致比较简单，可以看看如何进行实现的

- encoders.py：一个 JSON 解码的工具
- concurrency.py：相比 Starlette 添加了一个线程池上下文管理器
- datastructures.py：对 Starlette 的`UploadFile`进行了封装
- exception_handlers.py:增加了两种新的异常

  - async def http_exception_handler(request: Request, exc: HTTPException):
  - async def request_validation_exception_handler(request: Request,exc:RequestValidationError)

- exceptions.py： 增加了四种异常

  - HTTPException
  - FastAPIError
  - RequestValidationError
  - WebSocketRequestValidationError

- responses.py ： 增加了 UJSONResponse，ORJSONResponse
  - `orjson`是一种现在 **`python` 性能最高的 `json` 库**。有需求可以指定该种`response`。
