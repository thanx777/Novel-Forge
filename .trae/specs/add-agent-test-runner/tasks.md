# Tasks

- [x] Task 1: 创建后端测试执行引擎 `backend/test_runner.py`
  - [x] 1.1: 实现 `TerminalExecutor` - 执行 shell 命令，捕获 stdout/stderr/exit code，支持超时和 CWD
  - [x] 1.2: 实现 `CodeExecutor` - 执行 Python/Node.js 代码片段，写入临时文件后运行
  - [x] 1.3: 实现 `ApiTester` - 发送 HTTP 请求，返回状态码/headers/body
  - [x] 1.4: 实现 `PlaywrightRunner` - 执行 Playwright 测试脚本，截图并返回结果（可选依赖）
  - [x] 1.5: 实现安全过滤 - 拒绝危险命令（rm -rf /、format、del /s 等）
  - [x] 1.6: 实现统一入口 `execute_test(instruction)` - 解析 `[TEST:...]` 标记并路由到对应执行器

- [x] Task 2: 修改 `backend/main.py` - GraphExecutor 集成测试能力
  - [x] 2.1: 在 `_execute_node` 方法中，解析 LLM 输出中的 `[TEST:...]` 标记
  - [x] 2.2: 调用 `test_runner.execute_test()` 执行测试
  - [x] 2.3: 将测试结果通过 `yield_func` 发送到 SSE 日志流
  - [x] 2.4: 将测试结果注入当前节点的后续上下文（追加到 node output）
  - [x] 2.5: 修改 `FRAMEWORK_PROMPTS["reviewer"]` 添加测试指令说明
  - [x] 2.6: 修改 `FRAMEWORK_PROMPTS["manager"]` 添加测试指令说明

- [x] Task 3: 新增测试相关 API 端点
  - [x] 3.1: `POST /api/test/exec` - 手动触发测试（供未来扩展，当前主要被 Agent 内部调用）
  - [x] 3.2: `GET /api/test/capabilities` - 返回当前可用的测试能力（哪些已安装）

- [x] Task 4: 前端日志展示测试结果
  - [x] 4.1: 在 `translations.js` 中添加测试相关翻译 key
  - [x] 4.2: 在 `LogsPanel` 中为测试结果日志行添加特殊样式（test-success/test-fail/test-running）
  - [x] 4.3: 在 `App.css` 中添加测试日志行样式

- [x] Task 5: 创建测试相关 Skill 文件
  - [x] 5.1: `backend/skills/代码测试.skill.md` - 指导 Agent 如何测试代码文件
  - [x] 5.2: `backend/skills/Web测试.skill.md` - 指导 Agent 如何使用 Playwright 测试 Web 应用
  - [x] 5.3: `backend/skills/API测试.skill.md` - 指导 Agent 如何测试 API 接口

- [x] Task 6: 更新 `backend/requirements.txt`
  - [x] 6.1: 添加 `httpx` 依赖（API 测试）
  - [x] 6.2: 添加 `playwright` 为可选依赖注释

# Task Dependencies
- Task 2 depends on Task 1（GraphExecutor 需要 test_runner）
- Task 4 depends on Task 2（前端样式依赖后端日志格式）
- Task 5 depends on Task 1（Skill 需要 test_runner 已实现）
- Task 1, Task 3, Task 6 可并行
