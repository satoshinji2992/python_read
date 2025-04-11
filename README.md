# Python代码分析器

一个强大的Python代码分析工具，可以对Python源码进行深入分析，生成详细的文档和调试建议。该工具利用OpenAI的API，为源代码提供智能化解析和文档生成服务。

## 功能特点

- **代码分析**：解析Python文件的结构，包括导入模块、函数定义等
- **文档生成**：自动为函数生成详细文档，包括功能描述、参数用途和返回值含义
- **调试建议**：生成有针对性的调试建议，帮助开发者排查问题
- **变量分析**：追踪函数中的变量定义和使用情况
- **调用关系分析**：分析函数之间的调用关系
- **问题检测**：自动检测代码中可能存在的潜在问题

## 安装

### 前提条件

- Python 3.6+
- OpenAI API密钥

### 依赖安装

```bash
pip install openai
```

## 使用方法

### 环境变量设置

在使用之前，需要设置以下环境变量：

```bash
export API_KEY="你的OpenAI API密钥"
export BASE_URL=""https://api.deepseek.com""  # 可选，如使用非默认API端点
export MODEL_NAME="deepseek-chat"  # 可选，指定使用的模型
```

### 基本用法

分析Python文件并生成报告：

```bash
python python_read.py path/to/your_file.py
```

### 高级选项

```bash
# 使用两遍扫描模式（更详细的分析）
python python_read.py your_file.py --mode 1

# 只分析特定函数
python python_read.py your_file.py --function function_name

# 生成特定函数的调试建议
python python_read.py your_file.py --function function_name --debug
```

## 输出示例

### 分析报告

生成的Markdown格式分析报告包含以下部分：

1. **导入模块概览**：以表格形式展示导入的模块及其主要功能
2. **函数分析**：对每个函数的详细分析，包括：
   - 函数签名
   - 参数列表及类型
   - 返回值类型
   - 功能说明（AI生成）
   - 原始文档字符串（如果有）
   - 调用的其他函数
   - 变量使用情况
3. **潜在问题**：检测到的代码潜在问题列表
4. **报告示例**: [使用说明](./python_read_analysis.md)

### 调试建议

调试建议包含：
- 建议的日志插入点
- 函数参数的跟踪
- 结果返回前的检查点

## 工作原理

1. **源码解析**：使用Python的

ast

模块解析源代码
2. **模块信息收集**：收集导入模块的信息和函数文档
3. **函数提取**：提取源文件中的所有函数定义
4. **AI分析**：使用OpenAI API分析函数功能并生成文档
5. **变量与流程分析**：分析变量使用和函数调用关系
6. **报告生成**：汇总所有信息生成Markdown格式的详细报告

## 使用场景

- **代码审查**：快速理解大型项目或他人的代码
- **文档生成**：为缺少文档的代码自动生成文档
- **调试辅助**：获取有用的调试建议和代码流程分析
- **教育用途**：学习和理解Python代码结构和最佳实践

## 注意事项

- 需要有效的OpenAI API密钥才能使用文档生成功能
- 对于大型文件的分析可能需要更多的API调用，请注意API使用成本
- 生成的文档质量依赖于OpenAI模型的能力和使用的提示

## 许可协议

MIT许可证

## 贡献指南

欢迎通过Issues和Pull Requests进行贡献！

1. Fork本仓库
2. 创建您的特性分支：`git checkout -b feature/amazing-feature`
3. 提交您的更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交Pull Request