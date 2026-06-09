# Agent 驱动测试能力 Spec

## Why
当前 OmniAgent Hub 的 Reviewer/Manager 只能通过 LLM 文本判断代码质量，无法实际运行验证。Worker 生成的代码文件可能是语法错误、运行时崩溃或逻辑不正确的。需要让 Reviewer/Manager 在审阅时能实际执行代码/命令，获取真实运行结果来辅助判断。

## What Changes
- 后端新增测试执行引擎 `test_runner.py`，支持终端命令执行、代码运行、API 测试、Playwright 测试
- 后端新增 API 端点供 Agent 在执行流程中调用
- GraphExecutor 的 Reviewer/Manager 系统提示词增加测试指令说明
- Agent 可通过 `[TEST: ...]` 标记触发测试执行
- 前端仅在日志流中展示测试结果，不提供主动测试 UI
- 新增 4 个 Skill 文件指导 Agent 如何使用测试能力

## Impact
- Affected code: `backend/main.py`（GraphExecutor、API 路由）、`backend/test_runner.py`（新增）、前端日志展示
- Affected prompts: `FRAMEWORK_PROMPTS["reviewer"]`、`FRAMEWORK_PROMPTS["manager"]`
- 新增依赖: `httpx`（API 测试）、`playwright`（可选，Web 测试）

## ADDED Requirements

### Requirement: 测试执行引擎
系统 SHALL 提供后端测试执行引擎，支持以下四种测试模式：

1. **终端执行** - 执行 shell 命令并返回 stdout/stderr/exit code
2. **代码执行** - 运行 Python/Node.js 代码片段并返回输出
3. **API 测试** - 发送 HTTP 请求并返回响应状态码、头部、body
4. **Playwright 测试** - 启动浏览器执行 Web 自动化测试，返回截图和结果

#### Scenario: Reviewer 触发终端测试
- **WHEN** Reviewer 节点的 LLM 输出包含 `[TEST:CMD: npm run build]`
- **THEN** 系统在 workspace 目录下执行该命令
- **AND** 将 stdout/stderr/exit code 注入 Reviewer 的下一轮上下文
- **AND** 在 SSE 日志流中输出测试结果

#### Scenario: Reviewer 触发代码执行
- **WHEN** Reviewer 节点的 LLM 输出包含 `[TEST:CODE:python: print(1+1)]`
- **THEN** 系统执行该代码片段
- **AND** 将输出结果注入 Reviewer 的上下文

#### Scenario: Reviewer 触发 API 测试
- **WHEN** Reviewer 节点的 LLM 输出包含 `[TEST:API:GET: http://localhost:8000/api/presets]`
- **THEN** 系统发送 HTTP 请求
- **AND** 将响应状态码和 body 注入 Reviewer 的上下文

#### Scenario: Reviewer 触发 Playwright 测试
- **WHEN** Reviewer 节点的 LLM 输出包含 `[TEST:PW: navigate http://localhost:5173 and check button exists]`
- **THEN** 系统使用 Playwright 执行测试
- **AND** 将截图路径和测试结果注入 Reviewer 的上下文

#### Scenario: 测试超时
- **WHEN** 任何测试执行超过 60 秒
- **THEN** 系统终止执行并返回超时错误
- **AND** 不影响图谱其他节点的正常执行

#### Scenario: 测试命令安全限制
- **WHEN** Agent 尝试执行危险命令（rm -rf /、format、del /s 等）
- **THEN** 系统拒绝执行并返回安全警告

### Requirement: Agent 测试指令协议
系统 SHALL 在 Reviewer 和 Manager 的系统提示词中说明测试指令格式：

```
[TEST:CMD: <shell命令>]          - 终端执行
[TEST:CODE:<语言>: <代码>]       - 代码执行
[TEST:API:<方法>: <URL>]         - API 测试
[TEST:PW: <测试描述>]            - Playwright 测试
```

#### Scenario: Reviewer 审阅代码文件
- **WHEN** Reviewer 收到 Worker 产出的 Python 代码文件
- **THEN** Reviewer 可以使用 `[TEST:CODE:python: import 文件名; ...]` 实际运行验证
- **AND** 基于真实运行结果给出审阅结论

#### Scenario: Manager 检查构建结果
- **WHEN** Manager 检查 Worker 产出的前端项目
- **THEN** Manager 可以使用 `[TEST:CMD: npm run build]` 验证构建是否成功
- **AND** 基于构建结果决定是否继续或要求修改

### Requirement: 测试结果注入上下文
系统 SHALL 将测试执行结果自动注入触发测试的节点的后续上下文中。

#### Scenario: 测试结果格式
- **WHEN** 测试执行完成
- **THEN** 结果格式为：
  ```
  【测试结果】
  类型: 终端执行
  命令: npm run build
  退出码: 0
  输出: Build completed in 462ms
  耗时: 3.2s
  ```

### Requirement: 前端日志展示测试结果
系统 SHALL 在现有日志流中展示测试执行结果，无需新增 UI 面板。

#### Scenario: 测试结果在日志中显示
- **WHEN** 后端执行测试
- **THEN** SSE 日志流中输出测试状态（执行中/成功/失败）
- **AND** 前端 LogsPanel 中以特殊样式展示测试结果行

### Requirement: 可选 Playwright 依赖
系统 SHALL 将 Playwright 作为可选依赖，未安装时 `[TEST:PW:...]` 返回友好提示。

#### Scenario: Playwright 未安装
- **WHEN** Agent 使用 `[TEST:PW: ...]` 但 playwright 未安装
- **THEN** 系统返回 "Playwright 未安装，请运行: pip install playwright && playwright install chromium"
- **AND** 不影响其他测试模式的正常使用

## MODIFIED Requirements

### Requirement: Reviewer 系统提示词
Reviewer 的 FRAMEWORK_PROMPTS 增加测试能力说明：

原：
```
你是审查者。快速判断，不写论文。
【铁律】
- 审查结论+1-2句理由即可，50字以内
- 四种结论：通过 ✅ / 通过（附带建议）/ 需修改（指出1个关键问题）/ 不通过
- 合格就放行，不吹毛求疵
```

改为：
```
你是审查者。快速判断，不写论文。
【铁律】
- 审查结论+1-2句理由即可，50字以内
- 四种结论：通过 ✅ / 通过（附带建议）/ 需修改（指出1个关键问题）/ 不通过
- 合格就放行，不吹毛求疵

【测试能力】
你可以实际运行代码/命令来验证产出质量：
- [TEST:CMD: shell命令]          执行终端命令
- [TEST:CODE:python: 代码]       运行 Python 代码
- [TEST:CODE:node: 代码]         运行 Node.js 代码
- [TEST:API:GET: URL]            测试 API 接口
- [TEST:PW: 测试描述]            Playwright Web 测试（需安装）
测试结果会自动返回给你，基于真实结果做判断更可靠。
```

### Requirement: Manager 系统提示词
Manager 的 FRAMEWORK_PROMPTS 增加测试能力说明，在铁律部分追加：

```
- 你可以用 [TEST:CMD: 命令] 等测试指令验证执行者的产出是否可用
```
