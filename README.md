# Python 仓库代码分析工具

这是一个自动化的 Python 代码分析工具，它使用 AI 技术分析整个代码库，生成详细的代码分析报告、调试建议和仓库架构总结。该工具采用 REACT (Reason-Act-Reflect) 方法论，自动规划和执行代码分析流程。

## 主要功能

- **代码架构分析**：自动识别仓库中的 Python 文件，分析模块间依赖关系
- **函数级别分析**：详细分析每个函数的功能、参数、变量和调用关系
- **智能调试报告**：自动检测代码中的潜在问题和改进机会
- **仓库综合总结**：生成整个代码库的架构评估和高级概览
- **多文件并行处理**：支持并发分析多个文件以提高效率

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/python-repo-analyzer.git
cd python-repo-analyzer

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
python repo_read.py /path/to/your/repository
```

### 高级选项

```bash
python repo_read.py /path/to/your/repository --output /path/to/output/dir --concurrency 5 --debug
```

参数说明：
- `--output`：指定分析结果输出目录（默认为仓库下的 `_analysis` 目录）
- `--concurrency`：并发分析任务数量（默认为 5）
- `--debug`：启用调试模式，生成更详细的分析报告和 AI 综合总结

## 输出内容

成功运行后，在输出目录中将生成以下文件：

- `repo_overview.md`：仓库整体概览，包含文件列表、依赖关系和主要问题
- `repo_index.json`：模块和函数索引，包含依赖关系图
- `*_analysis.md`：每个 Python 文件的详细分析报告
- `*_debug.md`：每个 Python 文件的调试建议（仅在调试模式下生成）
- `repo_ai_summary.md`：AI 生成的仓库综合分析（仅在调试模式下生成）

## 工作原理

该工具采用三阶段分析方法：

1. **思考阶段 (Reason)**：自动收集仓库信息，识别入口点文件和关键模块，规划分析策略
2. **行动阶段 (Act)**：执行分析任务，并行处理多个文件，生成详细的分析和调试报告
3. **反思阶段 (Reflect)**：综合分析结果，构建全局索引和依赖图，生成仓库综合报告

!工作流程

## 环境设置

工具需要以下环境变量：

```
API_KEY=your_openai_api_key
BASE_URL=https://api.deepseek.com  # 可选，默认为 DeepSeek API
MODEL_NAME=deepseek-chat  # 可选，默认为 DeepSeek Chat 模型
```

可以在运行前设置这些环境变量：

```bash
export API_KEY=your_openai_api_key
```

## 示例

### 仓库概览示例

```markdown
# 代码仓库分析报告: my-python-project

**分析时间:** 2023-06-15 14:30:25

**仓库路径:** /path/to/my-python-project
**Python文件总数:** 15
**成功分析文件数:** 15

## 文件列表

| 文件 | 函数数 | 导入模块数 | 分析报告 | 调试报告 |
|------|--------|------------|----------|----------|
| app.py | 12 | 8 | [分析报告](app.py_analysis.md) | [调试报告](app.py_debug.md) |
| utils/helpers.py | 8 | 5 | [分析报告](helpers.py_analysis.md) | [调试报告](helpers.py_debug.md) |
...
```

## 贡献指南

欢迎贡献代码、文档或提出新功能建议！请按照以下步骤：

1. Fork 该项目
2. 创建您的功能分支：`git checkout -b feature/amazing-feature`
3. 提交您的更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交拉取请求

## 许可

该项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。

## 依赖项

- Python 3.7+
- aiohttp
- openai
- asyncio

## 常见问题解答

**Q: 分析大型仓库需要多久？**  
A: 取决于仓库大小和复杂度，以及并发设置。一个中等规模的仓库（约 50 个 Python 文件）大约需要 10-15 分钟。

**Q: 是否支持分析其他语言的代码？**  
A: 目前仅支持 Python 代码分析。未来计划添加对其他编程语言的支持。

**Q: API 使用量大吗？**  
A: 每个文件分析会使用一到两次 API 调用。对于大型仓库，建议关注 API 使用量。

---

*由 Python 代码分析工具自动生成的仓库分析示例可以在 示例目录 中找到。*