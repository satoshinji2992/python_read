import os
import sys
import asyncio
import argparse
import glob
import openai
from pathlib import Path
from datetime import datetime

# 设置 OpenAI API 参数
API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

# 初始化客户端
client = openai.OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
)

async def generate_repo_summary(analysis_dir, output_file=None):
    """生成仓库的综合总结报告"""
    print(f"正在生成仓库分析总结...")
    
    # 确保分析目录存在
    if not os.path.isdir(analysis_dir):
        print(f"错误: 分析目录 {analysis_dir} 不存在")
        return None
    
    # 如果没有指定输出文件，默认设置
    if not output_file:
        output_file = os.path.join(analysis_dir, "repo_summary.md")
    
    # 收集所有分析报告和调试报告
    analysis_files = glob.glob(os.path.join(analysis_dir, "*_analysis.md"))
    debug_files = glob.glob(os.path.join(analysis_dir, "*_debug.md"))
    overview_file = os.path.join(analysis_dir, "repo_overview.md")

    
    # 读取概览报告（如果存在）
    overview_content = ""
    if os.path.exists(overview_file):
        with open(overview_file, 'r', encoding='utf-8') as f:
            overview_content = f.read()
            print(f"已读取仓库概览报告")
    
    # 创建分析报告摘要
    analysis_summaries = {}
    for file_path in analysis_files:
        file_name = os.path.basename(file_path)
        module_name = file_name.replace("_analysis.md", "")
        
        # 读取分析报告内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 获取报告中的重要部分（例如，概述和主要功能）
            summary = extract_key_sections(content, ["概述", "主要功能", "关键组件"])
            if summary:
                analysis_summaries[module_name] = summary
    
    # 创建调试问题摘要
    debug_summaries = {}
    for file_path in debug_files:
        file_name = os.path.basename(file_path)
        module_name = file_name.replace("_debug.md", "")
        
        # 读取调试报告内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 获取报告中的问题部分
            issues = extract_key_sections(content, ["潜在bug分析", "问题", "错误", "改进建议"])
            if issues:
                debug_summaries[module_name] = issues
    
    # 准备输入给AI的内容
    ai_input = prepare_ai_input(overview_content, analysis_summaries, debug_summaries)
    
    # 使用AI生成仓库综合总结
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一位资深的软件架构师和代码审核专家，擅长分析代码仓库结构和提供改进建议。"},
                {"role": "user", "content": ai_input}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        summary_content = response.choices[0].message.content
        
        # 添加元数据和标题
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_report = f"""# 代码仓库综合分析总结

## 生成信息
- 生成时间: {timestamp}
- 分析文件数: {len(analysis_files)}
- 调试报告数: {len(debug_files)}

{summary_content}

---
*此报告由AI根据之前生成的代码分析和调试报告自动生成。内容可能需要专业人员进一步审核和验证。*
"""
        
        # 保存综合报告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_report)
        
        print(f"仓库综合总结报告已保存至: {output_file}")
        return output_file
    
    except Exception as e:
        error_msg = f"生成综合总结报告时出错: {str(e)}"
        print(error_msg)
        return None

def extract_key_sections(content, section_keywords):
    """从内容中提取关键部分"""
    extracted = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查标题是否包含关键词
        for keyword in section_keywords:
            if keyword.lower() in line.lower() and (line.startswith('#') or line.startswith('##') or line.startswith('###')):
                # 找到了关键部分的标题
                section = [line]
                i += 1
                
                # 继续读取，直到下一个标题或文件结束
                while i < len(lines) and not (lines[i].startswith('#') and len(lines[i]) > 2):
                    section.append(lines[i])
                    i += 1
                
                # 添加提取的部分
                extracted.append('\n'.join(section))
                i -= 1  # 回退一行，因为下一次循环会增加i
                break
        i += 1
    
    return '\n\n'.join(extracted)

def prepare_ai_input(overview, analysis_summaries, debug_summaries):
    """准备AI输入内容"""
    # 限制每个模块的摘要长度，防止超出令牌限制
    max_module_summary_length = 1500
    max_modules = 10
    
    input_content = """请根据以下代码仓库分析报告，生成一份全面的仓库总结。总结应包括：

1. 仓库总体结构和主要组件
2. 关键功能和模块的作用
3. 主要设计模式和架构特点
4. 代码质量评估和潜在问题
5. 建议的优化方向和改进措施

请用清晰的Markdown格式组织内容，突出重点，使报告既有技术深度又易于理解。

"""
    
    # 添加概览内容
    if overview:
        overview_excerpt = overview[:3000] + "..." if len(overview) > 3000 else overview
        input_content += f"\n## 仓库概览\n\n{overview_excerpt}\n\n"
    
    # 添加模块分析摘要
    if analysis_summaries:
        input_content += "\n## 模块分析摘要\n\n"
        
        # 限制模块数量
        module_names = list(analysis_summaries.keys())[:max_modules]
        for module in module_names:
            summary = analysis_summaries[module]
            if len(summary) > max_module_summary_length:
                summary = summary[:max_module_summary_length] + "..."
            
            input_content += f"### {module}\n\n{summary}\n\n"
        
        if len(analysis_summaries) > max_modules:
            input_content += f"... 以及其他 {len(analysis_summaries) - max_modules} 个模块\n\n"
    
    # 添加调试问题摘要
    if debug_summaries:
        input_content += "\n## 发现的问题和改进建议\n\n"
        
        # 限制模块数量
        module_names = list(debug_summaries.keys())[:max_modules]
        for module in module_names:
            issues = debug_summaries[module]
            if len(issues) > max_module_summary_length:
                issues = issues[:max_module_summary_length] + "..."
            
            input_content += f"### {module}\n\n{issues}\n\n"
        
        if len(debug_summaries) > max_modules:
            input_content += f"... 以及其他 {len(debug_summaries) - max_modules} 个模块的问题\n\n"
    
    input_content += """
请基于以上信息，提供一份有深度的综合分析，包括：
- 代码库的整体架构评估
- 关键模块之间的交互方式
- 主要的技术债务和潜在风险
- 可扩展性和维护性评估
- 具体的重构和改进建议

不需要简单复述上面的内容，而是要给出更高层次的洞察和建议。
"""
    
    return input_content

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Python代码仓库分析总结生成器")
    parser.add_argument("analysis_dir", help="存放分析报告的目录路径")
    parser.add_argument("--output", help="综合总结输出文件路径")
    
    args = parser.parse_args()
    
    await generate_repo_summary(args.analysis_dir, args.output)

if __name__ == "__main__":
    asyncio.run(main())