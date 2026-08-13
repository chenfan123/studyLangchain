import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from shopping_app.views.cart_views import shop
from user.my_center.my_center_views import MyCenter
from order.view.order_views import Order
app = FastAPI()
# 把项目下的static目录作为静态文件的访问目录
app.mount('/static',StaticFiles(directory='static'), name='static')

# 加载所有分路由
app.include_router(shop)
app.include_router(MyCenter)
app.include_router(Order)
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

# summary：总结摘要
# description: 接口的详细描述
@app.post("/test",tags=['给接口分组的标签'],summary='测试的接口',description='接口的详细描述',response_description='相应数据的详细描述')
def test():
    print("tes11t")
    return {"message": "test"}


# 启动服务
# 通过py运行，增加reload可以热重载
if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8000,reload=True)