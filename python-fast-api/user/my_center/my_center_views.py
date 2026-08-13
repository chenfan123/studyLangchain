from typing import Union, List

from fastapi import APIRouter, requests
from fastapi.params import Query

MyCenter = APIRouter(prefix='/user',tags=['user'])

@MyCenter.get('/user/my',summary="获取个人信息")
# 参数id和name可传可不传，2种方式
def my_center(id:Union[int,None]=None,name:str=Query(default=None,description="我的昵称")):
    print(id,name)
    return {"message":"ok"}

@MyCenter.get('/user/batch-update',summary='接受一组值')
# def my_batch_update(q:Union[List[str],None] = None):
def my_batch_update(q:List[str] = Query(default=[],description="多个id")):
    query_items = {"q":q}
    print(query_items,'query_items')
    return query_items