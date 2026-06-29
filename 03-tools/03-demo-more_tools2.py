from langchain.tools import tool
from langchain.messages import HumanMessage
import os
from langchain_core.utils.function_calling import convert_to_openai_tool
from dotenv import load_dotenv
from langchain_qwq import ChatQwen
from rich import print as rprint


# 从.env文件中加载环境变量
load_dotenv(override=True)

model = ChatQwen(
    model="deepseek-v4-flash",
    api_base=os.getenv("DASHSCOPE_API_BASE"),  # 国内 Key 必须用国内地址
)


@tool(parse_docstring=True)
def get_weather(city: str) -> str:
    """获取当日天气。

    Args:
    city: 城市名称
    """
    return f'{city}当天晴朗'


@tool(parse_docstring=True)
def get_news() -> str:
    """获取当日新闻。
    """
    return "近期，受全球储蓄芯片短缺等多重因素影响，多地回收商称废旧手机回收市场迎来“火热潮”，回收价格普遍上涨，旧手机成“香饽饽”。"


model_with_tools = model.bind_tools([get_weather, get_news])
rprint(convert_to_openai_tool(get_weather))
rprint(convert_to_openai_tool(get_news))
messages = [
    HumanMessage("今天杭州天气如何？今天新闻是什么？别瞎编")
]
response = model_with_tools.invoke(messages)
rprint("response", response)
messages.append(response)
for tool_call in response.tool_calls:
    if tool_call["name"] == "get_weather":
        tool_msg = get_weather.invoke(tool_call)
        rprint(tool_msg)
        messages.append(tool_msg)
    elif tool_call["name"] == "get_news":
        tool_msg = get_news.invoke(tool_call)
        rprint(tool_msg)
        messages.append(tool_msg)
    else:
        raise Exception("不存在的工具")

final_response = model.invoke(messages)

messages.append(final_response)
for msg in messages:
    msg.pretty_print()
