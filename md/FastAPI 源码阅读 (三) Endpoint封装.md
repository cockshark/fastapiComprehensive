### FastAPI 源码阅读 (三) Endpoint 封装

在 Starlette 中，请求的流动是基于 Scope 来实现的，到 endpoint 的前一步，将 Scope 封装成 Request
在 FastAPI 中，Route 节点 →Endpoint 的过程中,加入了大量逻辑，其中包括依赖判断，安全认证，数据类型判断等

在 FastAPI 中 APIRoute 实例化时，会对 endpoint 的参数进行解析。

> 这涉及到 inspect 库，他可以解析函数的参数，包括其注释的 Typing，以及其默认值，这为 id: str = Depends(get_id) 这样的表现形式提供了先决条件。

1. 配置 response model
2. 检查参数，搜集类型和依赖。构建 dependant。
3. 获取到 request 报文，参照 denpendant 将参数注入
4. 将返回值注入到 response model 中

### 依赖的配置

```python
 self.dependant = get_dependant(path=self.path_format, call=self.endpoint)
        for depends in self.dependencies[::-1]:
            self.dependant.dependencies.insert(
                0,
                get_parameterless_sub_dependant(depends=depends, path=self.path_format),
            )
```

使用了`get_dependant`函数，将`endpoint`传入进去。用来解析出`endpoint`的依赖项。随后将 dependencies 手动传入的依赖并入其中:

get_dependant → for get_param_sub_dependant → get_sub_dependant → get_dependant

1. 按节点寻找依赖项，将子节点的 dependant 加入到自身，向上返回 dependant 对象
2. 获取参数中依赖项的具体依赖函数
3. 将依赖函数进行判断，例如是否为安全相关，将其作为节点传入到 get_dependant 中

在这阶段中，`APIRoute`对`endpoint`进行解析，从中获取关于参数和`model`的信息。然后进行配置，将`APIRoute`自身适应化
