from urllib.request import Request

from fastapi import APIRouter, Body
from fastapi.params import Body
from pydantic import BaseModel, Field, field_validator

Order = APIRouter(prefix='/order',tags=['order'])

class Addr(BaseModel):
    street_address: str
    city: str
    state: str
    zip_code: str
    country: str
    phone:str
    email: str

class OrderData(BaseModel):
    id:str = Field(description="id")
    name:str = Field(description="name")
    order_id:str = Field(description="order_id")
    quantity:int = Field(description="quantity")
    price:float|int = Field(description="price",ge=100)
    address:Addr = Field(description="address")
    description:str = Field(description="description")
    # 自定义一个校验器
    @field_validator("description")
    def validate_description(cls, v):
        """
        :param v:
        :return:
        """
        import re
        result = re.match(r'^[a-z_]\w{5,16}$',v)
        # 断言，断言后面要接布尔类型
        assert not result is None
        return v

@Order.post("/add_order",tags=["order"],summary="创建订单")
async def add_order(order_data:OrderData):
    print(order_data,'order_data')
    return {"msg":"ok"}

@Order.post('/update_order',tags=["order"],summary='更新订单')
async def update_order(name:str = Body(default=None,description='订单名称'),price:float|int = Body(default=0.01,description="价格")):
    print(name,price,'order_data')
    return {"msg":"ok"}