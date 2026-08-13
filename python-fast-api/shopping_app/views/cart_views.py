from enum import Enum

from fastapi import APIRouter
from fastapi.params import Path

# 创建分路由，前缀是/shop
shop = APIRouter(prefix='/shop', tags=['shop'])

class ModelName(Enum):
    zs = '张三'
    ls = '李四 '

@shop.post('/cart',summary='查询购物车')
def find_cart():
    print('查询购物车')
    return {'msg':'得到购物车列表'}

@shop.post('/cart/create',summary='添加购物车')
def create_cart():
    print('添加购物车')
    return {'msg':"添加购物车"}

@shop.post('/cart/{detail_id}',summary='购物车商品详情')
def update_cart(detail_id: int):
    print('详情',detail_id)
    return {"msg" : "购物车详情"}

@shop.post('/cart/all/{model_name}',summary='')
def update_cart(model_name: ModelName = Path(description="这是对参数的描述")):
    print('详情',model_name.value,model_name.name)
    return {"msg" : "购物车详情"}

