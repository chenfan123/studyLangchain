from dotenv import load_dotenv
import os
from langchain_qwq import ChatQwen
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from rich import print as rprint
from langchain.messages import HumanMessage

# 从.env文件中加载环境变量
load_dotenv(override=True)

model = ChatQwen(
    model="deepseek-v4-flash",
    api_base=os.getenv("DASHSCOPE_API_BASE"),  # 国内 Key 必须用国内地址
)


class WeatherSchema(BaseModel):
    city: str = Field(description="城市名称")
    if_forecast: bool = Field(description="是否包含明日天气预报", default=False)


@tool("get_weather_and_forecast", description="查询当日天气，可以包含明日天气预报", args_schema=WeatherSchema)
def get_weather(city: str, if_forecast: bool):
    res = f"{city} 今天天气不错"
    if if_forecast:
        res += "\n明天也不错"
    return res


rprint(convert_to_openai_tool(get_weather))

# 注册工具
model_with_tools = model.bind_tools([get_weather])

# 消息列表
messages = [HumanMessage("今天杭州天气如何？明天呢？")]

# 调用模型
response = model_with_tools.invoke(messages)

# 添加响应消息
messages.append(response)
tool_calls = response.tool_calls
# 处理工具调用
for tool_call in tool_calls:
    if tool_call["name"] == "get_weather_and_forecast":
        # 调用工具
        tool_msg = get_weather.invoke(tool_call)
        # 添加工具调用消息
        messages.append(tool_msg)

# 最终响应
final_response = model_with_tools.invoke(messages)
# 添加最终响应消息
messages.append(final_response)
for msg in messages:
    msg.pretty_print()

rprint(messages)
