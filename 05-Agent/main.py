from agent import SmartAssistant
from init_model import model


# ==================== 主程序 ====================
def main():
    assistant = SmartAssistant(model=model)

    print("=" * 40)
    print("🤖 多功能智能助手（LangChain 1.2）")
    print("=" * 40)

    print("\n我可以帮你：")
    print(" 🌤 查询天气")
    print(" 🔢 数学计算")
    print(" ⏰ 时间查询")
    print(" 💱 货币转换")
    print(" 🔍 信息搜索")
    print("\n输入 'quit' 退出，输入 'reset' 重置对话\n")

    demos = [
        "北京今天天气怎么样？",
        "帮我算一下 (25 + 17) * 3",
        "现在几点了？",
        "100 美元等于多少人民币？",
    ]
    for demo in demos:
        print(f"👤 {demo}")
        response = assistant.chat(demo)
        print(f"🤖 {response}\n")

    # 重置对话
    assistant.reset()

    # 交互模式
    print("=" * 40)
    print("💬 进入交互模式")
    print("=" * 40)
    while True:
        user_input = input("\n👤 你: ")
        if user_input.lower() == "quit":
            print("再见！👋")
            break
        if user_input.lower() == "reset":
            assistant.reset()
            print("✅ 对话已重置")
            continue
        if not user_input.strip():
            continue

        # 调用助手
        response = assistant.chat(user_input)
        print(f"🤖 助手: {response}")


if __name__ == "__main__":
    main()
