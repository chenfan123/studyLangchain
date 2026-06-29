# 这个demo通过docstring来描述工具
import os
from dotenv import load_dotenv
from rich import print as rprint
from langchain_qwq import ChatQwen
from langchain_core.tools import tool
from langchain.messages import HumanMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

# 从.env文件中加载环境变量
load_dotenv(override=True)
model = ChatQwen(
    model="deepseek-v4-flash",
    api_base=os.getenv("DASHSCOPE_API_BASE"),  # 国内 Key 必须用国内地址
)


@tool("get_weather_and_forecast", parse_docstring=True)
def get_weather(city: str = "北京", if_forecast: bool = False):
    """查询当日天气，可以包含明日天气预报。

    Args:
        city: 城市名称
        if_forecast: 是否包含明日天气预报
    """
    res = f"{city} 今天天气不错"
    if if_forecast:
        res += "\n明天要下雨"
    return res


rprint(convert_to_openai_tool(get_weather))

model_with_tools = model.bind_tools([get_weather])
messages = [HumanMessage("今天杭州天气如何？明天呢？")]
response = model_with_tools.invoke(messages)
messages.append(response)
tool_calls = response.tool_calls
# 将工具调用的结果添加到消息列表中
for tool_call in tool_calls:
    if tool_call["name"] == "get_weather_and_forecast":
        # 返回值tool_msg类型是ToolMessage
        tool_msg = get_weather.invoke(tool_call)
        # 添加工具调用消息
        messages.append(tool_msg)
# 最终响应
final_response = model_with_tools.invoke(messages)
# 添加最终响应消息
messages.append(final_response)
for msg in messages:
    # 打印消息
    msg.pretty_print()

rprint(messages)
