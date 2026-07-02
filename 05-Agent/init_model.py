# 1、模型的初始化
import os
from dotenv import load_dotenv
from langchain_qwq import ChatQwen

# 从.env文件中加载环境变量
load_dotenv(override=True)
# 模型的初始化
model = ChatQwen(
    model="qwen3.6-27b",
    api_base=os.getenv("DASHSCOPE_API_BASE"),  # 国内 Key 必须用国内地址
)
