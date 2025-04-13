import python_read
import os
import asyncio
from python_read import PythonCodeAnalyzer
import aiofiles
import openai

API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

client = openai.OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
)


async def analyze_and_fix_repo(repo_path):
    """
    异步遍历代码仓库，分析每个 Python 文件
    """
    # 存储修复报告
    tasks = []

    # 遍历仓库中的所有 Python 文件
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                print(f"正在分析文件: {file_path}")

                # 异步分析文件
                tasks.append(analyze_file(file_path))

    # 并发执行所有任务
    results = await asyncio.gather(*tasks)

    # 打印完成信息
    for result in results:
        if result:
            print(f"分析完成! 报告已保存至: {result}")

async def analyze_file(file_path):
    """
    异步分析单个 Python 文件
    """
    # 初始化代码分析器
    analyzer = PythonCodeAnalyzer(file_path, model="deepseek-chat")

    # 加载文件
    if not analyzer.load_file():
        print(f"无法加载文件: {file_path}")
        return None

    # 异步生成报告
    report = await asyncio.to_thread(analyzer.generate_report)

    # 异步写入文件
    output_file = f"{file_path}_analysis.md"
    async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
        await f.write(report)

    return output_file

if __name__ == "__main__":
    # 替换为你的仓库路径
    repo_path = "/root/code/python/NetMamba_Project"
    asyncio.run(analyze_and_fix_repo(repo_path))