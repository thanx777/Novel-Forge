import asyncio
import subprocess
import tempfile
import os
import time
import re
import json

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))
DEFAULT_TIMEOUT = 60

DANGEROUS_PATTERNS = [
    r'rm\s+-rf\s+/', r'del\s+/s\s+/q\s+[a-zA-Z]:\\', r'format\s+[a-zA-Z]:',
    r'shutdown', r'reboot', r'mkfs', r'dd\s+if=', r':\(\)\{\s*:\|:\&\s*\}',
    r'curl\s+.*\|\s*sh', r'wget\s+.*\|\s*sh',
]


def is_dangerous(command: str) -> bool:
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, command, re.IGNORECASE):
            return True
    return False


class TestResult:
    def __init__(self, test_type, success, output="", error="", exit_code=None, duration=0, extra=None, needs_confirm=False):
        self.test_type = test_type
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code
        self.duration = duration
        self.extra = extra or {}
        self.needs_confirm = needs_confirm

    def to_text(self) -> str:
        lines = ["【测试结果】", f"类型: {self.test_type}"]
        if self.exit_code is not None:
            lines.append(f"退出码: {self.exit_code}")
        lines.append(f"结果: {'✅ 成功' if self.success else '❌ 失败'}")
        if self.output:
            out = self.output[:2000] + ("..." if len(self.output) > 2000 else "")
            lines.append(f"输出:\n{out}")
        if self.error:
            err = self.error[:500] + ("..." if len(self.error) > 500 else "")
            lines.append(f"错误:\n{err}")
        lines.append(f"耗时: {self.duration:.1f}s")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "test_type": self.test_type,
            "success": self.success,
            "output": self.output[:500],
            "error": self.error[:500],
            "exit_code": self.exit_code,
            "duration": self.duration,
            "needs_confirm": self.needs_confirm,
        }


async def terminal_executor(command: str, workspace_dir: str = None) -> TestResult:
    cwd = workspace_dir or WORKSPACE_DIR
    start = time.monotonic()

    if is_dangerous(command):
        return TestResult(
            test_type="CMD",
            success=False,
            error=f"⚠️ 危险命令需要确认: {command}",
            duration=0,
            needs_confirm=True,
            extra={"command": command},
        )

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=DEFAULT_TIMEOUT
        )
        duration = time.monotonic() - start
        return TestResult(
            test_type="CMD",
            success=proc.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode,
            duration=duration,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return TestResult(
            test_type="CMD",
            success=False,
            error=f"命令超时 ({DEFAULT_TIMEOUT}s)",
            exit_code=-1,
            duration=time.monotonic() - start,
        )
    except Exception as e:
        return TestResult(
            test_type="CMD",
            success=False,
            error=str(e),
            exit_code=-1,
            duration=time.monotonic() - start,
        )


async def execute_terminal_force(command: str, workspace_dir: str = None) -> TestResult:
    cwd = workspace_dir or WORKSPACE_DIR
    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=DEFAULT_TIMEOUT
        )
        duration = time.monotonic() - start
        return TestResult(
            test_type="CMD",
            success=proc.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode,
            duration=duration,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return TestResult(
            test_type="CMD",
            success=False,
            error=f"命令超时 ({DEFAULT_TIMEOUT}s)",
            exit_code=-1,
            duration=time.monotonic() - start,
        )
    except Exception as e:
        return TestResult(
            test_type="CMD",
            success=False,
            error=str(e),
            exit_code=-1,
            duration=time.monotonic() - start,
        )


async def terminal_executor_stream(command: str, workspace_dir: str = None):
    cwd = workspace_dir or WORKSPACE_DIR
    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        while True:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=DEFAULT_TIMEOUT)
            if not line:
                break
            yield {"type": "stdout", "data": line.decode("utf-8", errors="replace"), "elapsed": time.monotonic() - start}
        await proc.wait()
        yield {"type": "done", "exit_code": proc.returncode, "elapsed": time.monotonic() - start}
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        yield {"type": "error", "data": f"命令超时 ({DEFAULT_TIMEOUT}s)", "elapsed": time.monotonic() - start}
    except Exception as e:
        yield {"type": "error", "data": str(e), "elapsed": time.monotonic() - start}


async def code_executor(language: str, code: str, workspace_dir: str = None) -> TestResult:
    cwd = workspace_dir or WORKSPACE_DIR
    os.makedirs(cwd, exist_ok=True)
    start = time.monotonic()

    lang = language.lower().strip()
    if lang in ("python", "py"):
        ext = ".py"
        filename = "_test_temp.py"
        cmd_prefix = "python"
    elif lang in ("node", "nodejs", "javascript", "js"):
        ext = ".js"
        filename = "_test_temp.js"
        cmd_prefix = "node"
    else:
        return TestResult(
            test_type="CODE",
            success=False,
            error=f"不支持的语言: {language}",
            duration=time.monotonic() - start,
        )

    filepath = os.path.join(cwd, filename)
    real_path = os.path.abspath(filepath)
    if not real_path.startswith(os.path.abspath(cwd)):
        return TestResult(
            test_type="CODE",
            success=False,
            error="文件路径越权",
            duration=time.monotonic() - start,
        )

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        proc = await asyncio.create_subprocess_shell(
            f'{cmd_prefix} "{filepath}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=DEFAULT_TIMEOUT
        )
        duration = time.monotonic() - start
        return TestResult(
            test_type="CODE",
            success=proc.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode,
            duration=duration,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return TestResult(
            test_type="CODE",
            success=False,
            error=f"代码执行超时 ({DEFAULT_TIMEOUT}s)",
            exit_code=-1,
            duration=time.monotonic() - start,
        )
    except Exception as e:
        return TestResult(
            test_type="CODE",
            success=False,
            error=str(e),
            exit_code=-1,
            duration=time.monotonic() - start,
        )
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass


async def api_tester(method: str, url: str, workspace_dir: str = None) -> TestResult:
    start = time.monotonic()
    method = method.upper()

    try:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(method, url)
            duration = time.monotonic() - start
            body = response.text[:2000]
            return TestResult(
                test_type="API",
                success=200 <= response.status_code < 400,
                output=json.dumps({
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": body,
                }, ensure_ascii=False, indent=2),
                exit_code=response.status_code,
                duration=duration,
                extra={"status_code": response.status_code},
            )
        except ImportError:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(url, method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8", errors="replace")[:2000]
                    status = resp.status
                    headers = dict(resp.headers)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:2000]
                status = e.code
                headers = dict(e.headers)
            duration = time.monotonic() - start
            return TestResult(
                test_type="API",
                success=200 <= status < 400,
                output=json.dumps({
                    "status_code": status,
                    "headers": headers,
                    "body": body,
                }, ensure_ascii=False, indent=2),
                exit_code=status,
                duration=duration,
                extra={"status_code": status},
            )
    except asyncio.TimeoutError:
        return TestResult(
            test_type="API",
            success=False,
            error="请求超时 (30s)",
            exit_code=-1,
            duration=time.monotonic() - start,
        )
    except Exception as e:
        return TestResult(
            test_type="API",
            success=False,
            error=str(e),
            exit_code=-1,
            duration=time.monotonic() - start,
        )


async def playwright_runner(description: str, workspace_dir: str = None) -> TestResult:
    cwd = workspace_dir or WORKSPACE_DIR
    os.makedirs(cwd, exist_ok=True)
    start = time.monotonic()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return TestResult(
            test_type="PW",
            success=False,
            error="Playwright 未安装。请运行: pip install playwright && playwright install",
            duration=time.monotonic() - start,
        )

    url_match = re.search(r'https?://\S+', description)
    target_url = url_match.group(0) if url_match else "http://localhost:5173"

    script = f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("{target_url}", timeout=30000)
            title = await page.title()
            print(f"页面标题: {{title}}")
            buttons = await page.query_selector_all("button")
            print(f"按钮数量: {{len(buttons)}}")
            links = await page.query_selector_all("a")
            print(f"链接数量: {{len(links)}}")
            screenshot_path = "{os.path.join(cwd, '_pw_screenshot.png').replace(os.sep, '/')}"
            await page.screenshot(path=screenshot_path)
            print(f"截图已保存: {{screenshot_path}}")
        except Exception as e:
            print(f"错误: {{e}}")
        finally:
            await browser.close()

asyncio.run(main())
"""

    script_path = os.path.join(cwd, "_pw_test_temp.py")
    real_script_path = os.path.abspath(script_path)
    if not real_script_path.startswith(os.path.abspath(cwd)):
        return TestResult(
            test_type="PW",
            success=False,
            error="文件路径越权",
            duration=time.monotonic() - start,
        )

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        proc = await asyncio.create_subprocess_shell(
            f'python "{script_path}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=DEFAULT_TIMEOUT
        )
        duration = time.monotonic() - start
        screenshot_path = os.path.join(cwd, "_pw_screenshot.png")
        extra = {}
        if os.path.exists(screenshot_path):
            extra["screenshot"] = screenshot_path
        return TestResult(
            test_type="PW",
            success=proc.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode,
            duration=duration,
            extra=extra,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return TestResult(
            test_type="PW",
            success=False,
            error=f"Playwright 测试超时 ({DEFAULT_TIMEOUT}s)",
            exit_code=-1,
            duration=time.monotonic() - start,
        )
    except Exception as e:
        return TestResult(
            test_type="PW",
            success=False,
            error=str(e),
            exit_code=-1,
            duration=time.monotonic() - start,
        )
    finally:
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except OSError:
            pass


def parse_test_instructions(text: str) -> list:
    """解析所有 [TEST:CMD: ...] / [TEST:CODE:python: ...] 等测试指令。
    用手动括号计数处理嵌套的 []（Python 列表推导式等会含 ] 字符）。"""
    results = []
    prefix_pattern = re.compile(r'\[TEST:(?:CMD|API|PW|CODE:\w+):', re.IGNORECASE)
    for match in prefix_pattern.finditer(text):
        start = match.start()
        depth = 1
        i = match.end()
        while i < len(text) and depth > 0:
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
            i += 1
        if depth == 0:
            results.append(text[start:i])
    return results


async def execute_test(instruction: str, workspace_dir: str = None) -> TestResult:
    cwd = workspace_dir or WORKSPACE_DIR

    # 用括号计数提取 CMD 指令（支持命令内含 []，如 Python 列表推导）
    cmd_match = re.match(r'\[TEST:CMD:\s*', instruction, re.IGNORECASE)
    if cmd_match:
        start = cmd_match.end()
        depth = 1
        i = start
        while i < len(instruction) and depth > 0:
            if instruction[i] == '[':
                depth += 1
            elif instruction[i] == ']':
                depth -= 1
            i += 1
        if depth == 0:
            cmd = instruction[start:i-1].strip()
            return await terminal_executor(cmd, cwd)
    if cmd_match:
        return await terminal_executor(cmd_match.group(1).strip(), cwd)

    code_match = re.match(r'\[TEST:CODE:(\w+):\s*(.+)\]$', instruction, re.IGNORECASE | re.DOTALL)
    if code_match:
        return await code_executor(code_match.group(1), code_match.group(2).strip(), cwd)

    api_match = re.match(r'\[TEST:API:(\w+):\s*(.+)\]$', instruction, re.IGNORECASE)
    if api_match:
        return await api_tester(api_match.group(1), api_match.group(2).strip(), cwd)

    pw_match = re.match(r'\[TEST:PW:\s*(.+)\]$', instruction, re.IGNORECASE | re.DOTALL)
    if pw_match:
        return await playwright_runner(pw_match.group(1).strip(), cwd)

    return TestResult(
        test_type="UNKNOWN",
        success=False,
        error=f"无法解析测试指令: {instruction}",
        duration=0,
    )
