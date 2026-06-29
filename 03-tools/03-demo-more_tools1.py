# 大模型调用工具是单次推理，每次运行调用一个工具，当调用多个工具时，需要用户自己管理多次调用循环。
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import os
from langchain_core.utils.function_calling import convert_to_openai_tool
from rich import print as rprint
from langchain_qwq import ChatQwen
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal

# 从.env文件中加载环境变量
load_dotenv(override=True)

model = ChatQwen(
    model="deepseek-v4-flash",
    api_base=os.getenv("DASHSCOPE_API_BASE"),  # 国内 Key 必须用国内地址
)

# 1.定义工具
# 定义股票查询工具


class StockPriceInput(BaseModel):
    company: str = Field(
        description="公司名称（如：苹果公司, 微软公司, 谷歌公司）"
    )
    timeframe: Literal["today", "week", "month"] = Field(
        default="today",
        description="时间范围（today-今日, week-本周, month-本月）"
    )


@tool(args_schema=StockPriceInput, parse_docstring=True, description="获取指定公司的股票价格信息")
def get_stock_price(company: str, timeframe: str = "today") -> str:
    # 模拟股票数据
    mock_data = {
        "苹果公司": {"today": 185.20, "week": 183.50, "month": 180.75},
        "微软公司": {"today": 415.86, "week": 412.30, "month": 405.42},
        "谷歌公司": {"today": 15.42, "week": 15.20, "month": 14.85}
    }
    if company in mock_data:
        price = mock_data[company].get(timeframe, "未知时间范围")
        return f"{company} {timeframe}价格: {price}美元"
    else:
        return f"未找到股票代码 {company} 的数据"

# 定义新闻搜索工具


@tool(parse_docstring=True)
def search_news(company: str) -> str:
    """搜索指定公司的财经新闻。

    Args:
        company: 公司名称

    Returns:
        公司的财经新闻，每个新闻占一行
    """
    # 模拟新闻数据
    mock_news = {
        "苹果公司": [
            "苹果发布新款iPhone，股价上涨3%",
            "苹果与欧盟达成反垄断和解协议",
            "苹果将在印度扩大生产规模"
        ],
        "微软公司": [
            "微软Azure云业务季度增长超预期",
            "微软完成对Nuance的收购",
            "微软推出新一代AI助手Copilot"
        ],
        "谷歌公司": [
            "谷歌发布新AI模型，性能提升20%",
            "谷歌与OpenAI合作，开发新的AI助手",
            "谷歌在欧洲展开AI研究项目"
        ]
    }
    news_list = mock_news.get(company, [f"未找到{company}的相关新闻"])
    return "\n".join(news_list)


# rprint(convert_to_openai_tool(search_news))
rprint(convert_to_openai_tool(get_stock_price))

# 2.初始化模型并绑定工具
tools = [get_stock_price, search_news]
model_with_tools = model.bind_tools(tools)

message_list = []
# human_message = HumanMessage(content="苹果公司今天的股价是多少？最近有什么新闻？")
# human_message = HumanMessage(content="比较一下微软和苹果的股价")
human_message = HumanMessage(content="腾讯最近有什么重大新闻？")
# human_message = HumanMessage(content="海水为什么是咸的？")
message_list.append(human_message)

# 3.工具调用
while True:
    response = model_with_tools.invoke(message_list)
    rprint("response", response)
    message_list.append(response)
    # 如果模型不需要调用工具，直接退出循环
    if not response.tool_calls:
        rprint("没有工具调用，直接返回答案")
        break
    # 如果有调用工具，处理工具调用响应
    # 4.开发者根据模型的响应，调用工具并获取结果
    for tool_call in response.tool_calls:
        if tool_call["name"] == "get_stock_price":
            # 调用股票查询工具
            stock_result = get_stock_price.invoke(tool_call)
            rprint("stock_result", stock_result)
            message_list.append(stock_result)
        if tool_call["name"] == "search_news":
            # 调用新闻搜索工具
            news_result = search_news.invoke(tool_call)
            rprint("news_result", news_result)
            message_list.append(news_result)
# 最终响应
# print("response", response)
# print(response.content)
for msg in message_list:
    msg.pretty_print()
