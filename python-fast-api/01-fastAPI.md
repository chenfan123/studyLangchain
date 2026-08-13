# FastAPI

### ASGI 协议和服务

WSGI: web 服务器网关接口，是一种 web 服务器网关接口，是一个 web 服务器与 web 应用通信的一种规范。

ASGI: 一部 8 网管协议接口，一个介于网络协议服务和 python 应用之间的标准接口，能够处理多种通用的协议类型，包括 http、http2 和 websocket。当前运行在 ASGI 协议之上的 Web 框架有 FastAPI，Django 等。

## 虚拟环境

`python3 -m venv fastapi_env`创建虚拟环境
`source fastapi_env/bin/activate`激活虚拟环境

## conda虚拟环境
创建虚拟环境：`conda create -n fastapi_env python=3.12`
激活虚拟环境：`conda activate fastapi_env`
退出虚拟环境：`conda deactivate`
安装FastAPI：`pip install "fastapi[standard]"`



## 启动方式
### 三种
1. pycharm 启动按钮（开发模式）
2. 通过uvicorn命令启动（生产模式）
    uvicorn main:app --reload
        main: main.py文件
        app:在main.py文件中通过app = FastAPI()创建的对象
        --reload:让服务器在更新代码后重新启动
3. 在main.py中定义main函数
4. 

## 路由分发
1. 创建分路由,需要APIRouter `shop = APIRouter(prefix='/shop', tags=['shop'])`
2. 书写路由函数即可
3. main.py中需要import对应的分路由`from shopping_app.views.cart_views import shop`
4. 加载所有分路由`app.include_router(shop)`

## 路由传参
1. 路径参数的值会作为参数传递给函数
2. FastAPI会通过类型声明对请求自动解析
3. 预设值使⽤标准的 Python Enum 类型。表示传参的时候只能传哪些值
注：
> 由于路由匹配操作是按顺序依次运行的，所以需要保证`\user\all`在`\user\{id}`之前，不然会被匹配给id


## 请求传参
1. 请求参数是通过URL请求地址携带的`http://12.7.0.0.1/item?a=1`,都在?之后
2. 参数通过Query可以设置为可传可不传`name:str=Query(default=None,description="我的昵称")`或者通过`Union[xx,None]=None`

### 一个参数名，多个值
需要把行参设置为List
```python
@MyCenter.get('/user/batch-update',summary='接受一组值')
def my_batch_update(q:List[str] = Query(default=[],description="多个id")):
    query_items = {"q":q}
    print(query_items,'query_items')
    return query_items
```

## 参数校验
Query时专门用来装饰URL请求参数的类，也可以提供校验。
1. 默认值设置，和参数接口描述`Query(default=[],description="多个id")`
2. 字符串长度校验：`Query(default=None, max_length=15,min_length=6)`
3. 正则表达式`Query(default=None, regex="^laoxiao$")`
4. 数值大小校验`Query(description="id参数必须是0到1000之间", gt=0)` 
    - gt:大于
    - ge:大于等于
    - lt:小于
    - le:小于等于
> 断言：assert后面必须接布尔类型，表示我确信这个条件一定成立，否则就说明程序存在问题

## 请求体传参
要将数据从客⼾端(例如浏览器)发送给API时,你将其作为[请求体] （request body）发送,请求体
是客⼾端发送给API的数据.响应体是API发送给客⼾端的数据。

## 请求总结
- 请求体单个传参 Body 
- 路由传参 Path
- URL传参 Query