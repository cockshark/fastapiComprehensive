### fastapi 源码分析(1) ASGI 应用

```python
class FastAPI(Starlette):
    def openapi(self) -> Dict[str, Any]:pass
    def setup(self) -> None:pass
    def add_api_route
    def api_route
    def add_api_websocket_route
    def websocket
    def include_router
	...
    def trace
```

`openapi()`与`setup()`是在初始化阶段，对**OpenAPI**文档进行初始化的函数

而`add_api_route()`一直到`trace()`，是关于路由的函数，它们都是直接对`router`的方法传参引用。

#### \_\_init\_\_()参数解析

源码：

```python
    def __init__(
        self,
        *,
        debug: bool = False,
        routes: Optional[List[BaseRoute]] = None,
        title: str = "FastAPI",
        description: str = "",
        version: str = "0.1.0",
        openapi_url: Optional[str] = "/openapi.json",
        openapi_tags: Optional[List[Dict[str, Any]]] = None,
        servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
        dependencies: Optional[Sequence[Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",
        swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
        swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        exception_handlers: Optional[
            Dict[
                Union[int, Type[Exception]],
                Callable[[Request, Any], Coroutine[Any, Any, Response]],
            ]
        ] = None,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        openapi_prefix: str = "",
        root_path: str = "",
        root_path_in_servers: bool = True,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        **extra: Any,
    ) -> None:
        self._debug: bool = debug
        self.state: State = State()
        # 这里路由用的是APIRouter，和starlette所采用的不同
        self.router: routing.APIRouter = routing.APIRouter(
            routes=routes,
            dependency_overrides_provider=self,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            default_response_class=default_response_class,
            dependencies=dependencies,
            callbacks=callbacks,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            responses=responses,
        )
        self.exception_handlers: Dict[
            Union[int, Type[Exception]],
            Callable[[Request, Any], Coroutine[Any, Any, Response]],
        ] = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self.exception_handlers.setdefault(HTTPException, http_exception_handler)
        self.exception_handlers.setdefault(
            RequestValidationError, request_validation_exception_handler
        )

        self.user_middleware: List[Middleware] = (
            [] if middleware is None else list(middleware)
        )
        self.middleware_stack: ASGIApp = self.build_middleware_stack()

        self.title = title
        self.description = description
        self.version = version
        self.servers = servers or []
        self.openapi_url = openapi_url
        self.openapi_tags = openapi_tags
        # TODO: remove when discarding the openapi_prefix parameter
        if openapi_prefix:
            logger.warning(
                '"openapi_prefix" has been deprecated in favor of "root_path", which '
                "follows more closely the ASGI standard, is simpler, and more "
                "automatic. Check the docs at "
                "https://fastapi.tiangolo.com/advanced/sub-applications/"
            )
        self.root_path = root_path or openapi_prefix
        self.root_path_in_servers = root_path_in_servers
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.swagger_ui_oauth2_redirect_url = swagger_ui_oauth2_redirect_url
        self.swagger_ui_init_oauth = swagger_ui_init_oauth
        self.extra = extra
        self.dependency_overrides: Dict[Callable[..., Any], Callable[..., Any]] = {}

        self.openapi_version = "3.0.2"

        if self.openapi_url:
            assert self.title, "A title must be provided for OpenAPI, e.g.: 'My API'"
            assert self.version, "A version must be provided for OpenAPI, e.g.: '2.1.0'"
        self.openapi_schema: Optional[Dict[str, Any]] = None
        self.setup()
```

参数解释：

```python
        # starlette原生
        :param debug: debug模式
        :param middleware: 中间件列表
        :param exception_handlers: 异常对应处理的字典
        :param on_startup: 启动项列表
        :param on_shutdown: 结束项列表
        :param routes: 路由列表

        # OpenAPI文档相关
        :param docs_url: API文档地址
        :param title: 标题
        :param description: 描述
        :param version: API版本
        :param openapi_url: openapi.json的地址
        :param openapi_tags: 上述内容的元数据模式

        # 文档的页面中的OAuth，有关JS
        :param swagger_ui_oauth2_redirect_url:
        :param swagger_ui_init_oauth:

        # Redoc文档
        :param redoc_url: 文档地址

        # 反向代理情况下的文档
        :param servers: 服务器列表
        :param openapi_prefix: 支持反向代理和挂载子应用程序，已被弃用
        :param root_path: 如果有反向代理，让app直到自己"在哪"
        :param root_path_in_servers: 允许自动包含root_path

        :param default_response_class: 默认的response类
        :param extra:
```

#### root_path 和 servers 参数

主要是关于文档与反向代理的参数：参考官方文档 : [fastapi-behind-a-proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/)

当使用了 Nginx 时等反向代理时，从 Uvicorn 直接访问，和从 Nginx 代理访问，路径可能出现不一致。

```markdown
比如 Nginx 中的 Fastapi 根目录是`127.0.0.1/api/`，而 Uvicorn 角度看是`127.0.0.1:8000/`。对于 API 接口来说，其实这个是没有影响的，因为服务器会自动帮我们解决这个问题。但对于 API 文档来说，就会出现问题。

当我们打开/docs 时，网页会寻找 openapi.json。他的是写在 html 内部的，而不是变化的。
```

##### 这会导致什么问题？

- 不经过反向代理

```markdown
当我们从 Uvicorn 访问 127.0.0.1:8000/docs 时，他会寻找/openapi.json,即去访问 127.0.0.1:8000/openapi.json

- localhost（local）是不经网卡传输！这点很重要，它不受网络防火墙和网卡相关的的限制。
- 127.0.0.1 是通过网卡传输，依赖网卡，并受到网络防火墙和网卡相关的限制。
  当然这两点和上面的问题无关
```

- 经过反向代理

从 Nginx 外来访问文档，假设我们这样设置 Nginx:

```shell
location /api/ {
            proxy_pass   http://127.0.0.1:8000/;
        }
```

我们需要访问`127.0.0.1/api/docs`，才能从代理外部访问。而打开 docs 时，我们会寻找**openapi.json**。

所以这时，它应该在`127.0.0.1/api/openapi`这个位置存在。

但我们的浏览器不知道这些，他会按照`/openapi.json`，会去寻`127.0.0.1/openapi.json`这个位置。

所以他不可能找到**openapi.json**，自然会启动失败。

**这本质是 openapi 文档前端问题**

**而 root_path 就是用来解决这个问题的**：既然`/openapi.json`找不到，那我自己改成`/api/openapi.json`不就成了么。

**root_path**即是这个`/api`，这个是在定义时手动设置的参数。为了告诉 FastAPI，它处在整个主机中的哪个位置。即告知 **所在根目录**。这样，FastAPI 就有了"自知之明"，乖乖把这个**前缀**加上。来找到正确的**openapi.json**

加上了**root_path**，**openapi.json**的位置变成了`/api/openapi.json`。当你想重新用 Uvicorn 提供的地址从代理内访问时，他会去寻找哪？没错`127.0.0.1:8000/api/openapi.json`，但我们从代理内部访问，并不需要这个**前缀**，但它还是**“善意”**的帮我们加上了，所以这时候内部的访问失灵了！！！！。

**_不过应该没人要用两种方式访问同一个 doc 吧。。。_**

```markdown
弃用了 openapi_prefix 参数,root_path 有啥用？
```

- 提到**servers**这个参数

```python
from fastapi import FastAPI, Request

app = FastAPI(
    servers=[
        {"url": "https://stag.example.com", "description": "Staging environment"},
        {"url": "https://prod.example.com", "description": "Production environment"},
    ],
    root_path="/api",
)


@app.get("/test")
def read_main(request: Request):
    return {"message": "Hello World", "root_path": request.scope.get("root_path")}
```

![多了许多内容](..\assets\images\server_rootpath_test.webp)

我们可以切换这个**Servers**时，底下测试接口的发送链接也会变成相应的。

![/api](..\assets\images\api.png)

![stag.example.com](..\assets\images\stag.example.com.png)

**但是记住，切换这个 server，下面的接口不会发送变化，只是发送的 host 会改变。**

这代表，虽然可以通过文档，测试多个其他主机的接口。但是这些主机和自己之间，需要拥有一致的接口。这种情况通常像在**线上/开发服务器**或者**服务器集群**中可能出现。虽然不要求完全一致，但为了这样做有实际意义，最好大体上是一致的。

但是我们看到，这是在代理外打开的，如果我们想从代理内打开，需要去掉**root_path**。会发生什么？

我们将**root_path**注释掉：

![依旧可以访问](..\assets\images\依旧可以访问.png)

很好，我们依旧可以看到这些服务器，但是。
**我们找不到自己了**，我们可以在这两个服务器之间来回切换，但是无法切到自己。我们无法访问自己的接口。

如果想解决这个问题，只需要将自身手动加入到`Servers`中。

```python
from fastapi import FastAPI, Request

app = FastAPI(
    servers=[
        {"url": "/", "description": "这是你自己哦"},
        {"url": "https://stag.example.com", "description": "Staging environment"},
        {"url": "https://prod.example.com", "description": "Production environment"},
    ],
    # root_path="/api/",
)

@app.get("/test")
def read_main(request: Request):
    return {"message": "Hello World", "root_path": request.scope.get("root_path")}
```

看看文档：

![有了自己的一席之地](..\assets\images\有了自己的一席之地.webp)

### root_path-servers 总结

- root_path 和 servers 都是关于 api 文档的内容，只影响文档，不影响代理内外 api 的访问。
- root_path 可以在反向代理的情况下，让 api 文档确认到自己的位置
- servers 可以让 API 文档访问多个服务器，但如果没有添加 root_path 就无法找到自己
- root_path × servers × 非代理，不显示选项，仅访问自己。代理，找不到 openapi.json
- root_path v servers × 非代理，找不到 openapi.json。代理，显示选项，仅访问自己
- root_path × servers v 非代理，显示选项，无法访问自己。代理，找不到 openapi.json
- root_path v servers v 非代理，找不到 openapi.json。代理，显示选项，都可以访问

1. root_path 的有无 决定你能在代理内还是外访问到 openapi。
2. 没有 servers 时，默认访问自己。有 servers 时，按 servers 里的内容来。
3. 如果 servers 没有自己，那就是无法访问自己。
4. root_path 非空时，会自动把自己加入到 servers 中
5. root_path 为空时，想访问自己，请手动写'/'到 servers 中
6. root_path_in_servers 会决定 ④ 是否把自动把自己加入到 servers 中

关于**root_path_in_servers**，当**root_path**和**servers**都存在时，**root_path**会自动将自己加入到**servers**中。但如果这个置为 False，就不会自动加入。(默认为 True)

### 路由的添加与装饰器

```python
    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Coroutine[Any, Any, Response]],
        *,
        response_model: Optional[Type[Any]] = None,
        status_code: Optional[int] = None,
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[Depends]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        deprecated: Optional[bool] = None,
        methods: Optional[List[str]] = None,
        operation_id: Optional[str] = None,
        response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        response_model_by_alias: bool = True,
        response_model_exclude_unset: bool = False,
        response_model_exclude_defaults: bool = False,
        response_model_exclude_none: bool = False,
        include_in_schema: bool = True,
        response_class: Union[Type[Response], DefaultPlaceholder] = Default(
            JSONResponse
        ),
        name: Optional[str] = None,
        openapi_extra: Optional[Dict[str, Any]] = None,
        generate_unique_id_function: Callable[[routing.APIRoute], str] = Default(
            generate_unique_id
        ),
    ) -> None:
        self.router.add_api_route(
            path,
            endpoint=endpoint,
            response_model=response_model,
            status_code=status_code,
            tags=tags,
            dependencies=dependencies,
            summary=summary,
            description=description,
            response_description=response_description,
            responses=responses,
            deprecated=deprecated,
            methods=methods,
            operation_id=operation_id,
            response_model_include=response_model_include,
            response_model_exclude=response_model_exclude,
            response_model_by_alias=response_model_by_alias,
            response_model_exclude_unset=response_model_exclude_unset,
            response_model_exclude_defaults=response_model_exclude_defaults,
            response_model_exclude_none=response_model_exclude_none,
            include_in_schema=include_in_schema,
            response_class=response_class,
            name=name,
            openapi_extra=openapi_extra,
            generate_unique_id_function=generate_unique_id_function,
        )
```

以上核心只是调用了一个 router 的一个功能：
有的直接调用转发，还有些使用了闭包。**FastAPI**添加路由的方式，在 starlette 的传统路由列表方式上做了改进，变成了装饰器式。

```python
@app.get('/path')
def endport():
    return {"msg": "hello"}
```

其实就是通过这些方法作为装饰器，将自身作为 endpoint 传入生成 route 节点，加入到 routes 中。

### App 入口

```python
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.root_path:
            scope["root_path"] = self.root_path
        await super().__call__(scope, receive, send)
```

新版本更新的比较简洁：FastAPI 的入口没有太大的变化，借用 starlette 的 await self.middleware_stack(scope, receive, send)直接进入中间件堆栈。
