# Example 使用说明

## open_multiple_profiles.py

这个脚本用于批量打开多个 MoreLogin 浏览器配置文件，并在每个配置文件中打开指定的网页。

### 使用方法

1. **编辑配置文件**
   
   打开 `config.yaml` 文件，修改配置参数：

   ```yaml
   # 环境ID列表 - 要打开的浏览器配置文件ID
   env_ids:
     - "1907751741233373184"
     - "1907751741233373185"
     - "1907751741233373186"

   # 目标URL - 要在每个环境中打开的网页地址
   target_url: "https://grvt.io/exchange/perpetual/BTC-USDT"

   # API配置
   api:
     base_url: "http://localhost:40000"
     timeout: 10

   # 浏览器配置
   browser:
     page_load_timeout: 30000
     wait_until: "networkidle"

   # 等待时间配置（秒）
   delays:
     after_browser_start: 1
     between_profiles: 0.5
   ```

2. **设置环境ID**
   
   在 `config.yaml` 中的 `env_ids` 列表中添加你的环境ID。

3. **修改其他配置（可选）**
   
   - `target_url`: 要打开的网页地址
   - `api.base_url`: MoreLogin API 地址（默认 localhost:40000）
   - `api.timeout`: API 请求超时时间（秒）
   - `browser.page_load_timeout`: 页面加载超时时间（毫秒）
   - `browser.wait_until`: 页面加载等待策略
   - `delays.after_browser_start`: 浏览器启动后等待时间（秒）
   - `delays.between_profiles`: 打开下一个环境前的等待时间（秒）

4. **安装依赖**
   
   ```bash
   pip install pyyaml playwright requests
   ```

5. **运行脚本**
   
   ```bash
   cd Example
   python open_multiple_profiles.py
   ```

### 功能特点

- ✅ 批量打开多个浏览器配置文件
- ✅ 自动在每个环境中打开指定页面
- ✅ 详细的日志输出，显示每个环境的处理状态
- ✅ 错误处理：单个环境失败不影响其他环境
- ✅ 支持保持浏览器打开（默认行为）
- ✅ 支持 Ctrl+C 优雅退出并关闭所有环境

### 注意事项

1. **前置条件**
   - 确保 MoreLogin 客户端已启动并成功登录
   - 确保 MoreLogin 版本 >= 2.32
   - 确保已安装依赖: `pip install pyyaml playwright requests`

2. **环境ID获取**
   
   可以使用 `../MoreLogin-Python/list_browser_profiles.py` 来获取你的环境ID列表。

3. **脚本行为**
   - 脚本会依次打开每个环境（不是并行）
   - 浏览器会保持打开状态，直到你按 Ctrl+C
   - 按 Ctrl+C 后，脚本会尝试关闭所有已打开的环境

4. **自动关闭（可选）**
   
   如果希望脚本运行一段时间后自动关闭所有环境，可以取消脚本末尾的注释：
   
   ```python
   time.sleep(30)  # 等待30秒
   for env_id in opened_profiles:
       stop_profile(env_id)
   ```

### 示例输出

```
准备打开 3 个环境配置文件
目标URL: https://grvt.io/exchange/perpetual/BTC-USDT
------------------------------------------------------------

[1/3] 处理环境: 1907751741233373184
[环境 1907751741233373184] 启动成功，CDP URL: http://127.0.0.1:9222
[环境 1907751741233373184] 正在打开页面: https://grvt.io/exchange/perpetual/BTC-USDT
[环境 1907751741233373184] 页面加载完成，标题: GRVT Exchange

[2/3] 处理环境: 1907751741233373185
...

============================================================
成功打开 3/3 个环境
浏览器将保持打开状态，按 Ctrl+C 退出
============================================================
```

