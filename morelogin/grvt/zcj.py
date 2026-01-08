"""
打开多个浏览器配置文件并在每个配置文件中打开指定页面
"""

import os
import sys
import time
import random
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from playwright.sync_api import sync_playwright
import requests
import yaml

os.environ.setdefault("NODE_OPTIONS", "--no-deprecation")

# 添加项目根目录到 Python 路径
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from adapters import create_adapter

def build_target_url(config: dict) -> str | None:
    """构建目标URL"""
    if pair := config.get("trading_pair"):
        if pair := pair.strip().upper():
            return f"https://grvt.io/exchange/perpetual/{pair}"
    if url := config.get("target_url"):
        return url.strip() if url.strip() else None
    return None

def load_config() -> dict:
    """加载配置文件并返回所有配置项"""
    with open(script_dir / "config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 处理环境ID列表
    env_ids = config.get("env_ids", [])
    if isinstance(env_ids, str):
        # 如果是字符串，按逗号分割
        env_ids = [e.strip() for e in env_ids.split(",") if e.strip()]
    elif not isinstance(env_ids, list):
        env_ids = []
    
    return {
        "env_ids": env_ids,
        "target_url": build_target_url(config),
        "api_base_url": config.get("api", {}).get("base_url", "http://localhost:40000"),
        "api_timeout": config.get("api", {}).get("timeout", 10),
        "api_close_timeout": config.get("api", {}).get("close_timeout", 5),
        "page_load_timeout": config.get("browser", {}).get("page_load_timeout", 30000),
        "wait_until": config.get("browser", {}).get("wait_until", "networkidle"),
        "delay_after_browser_start": config.get("delays", {}).get("after_browser_start", 1),
        "delay_between_profiles": config.get("delays", {}).get("between_profiles", 0.5),
        "trading_pair": config.get("trading_pair", "").strip().upper() if config.get("trading_pair") else None,
        "price_offset": config.get("trading", {}).get("price_offset", 0.0001),
        "amount": config.get("trading", {}).get("amount", 0.001),
        "position_check_interval": config.get("trading", {}).get("position_check_interval", 3),
    }

def convert_trading_pair_to_symbol(trading_pair: str) -> str:
    """转换交易对格式: "BTC-USDT" -> "BTC_USDT_Perp" """
    return f"{trading_pair.replace('-', '_')}_Perp"

def get_position(grvt, symbol: str, max_retries: int = 3, retry_delay: float = 1.0) -> float:
    """
    获取账号当前持仓（带重试机制）
    
    Args:
        grvt: GrvtCcxt实例（已废弃，保留以兼容旧代码）
        symbol: 交易对符号
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    
    Returns:
        持仓数量，如果失败返回0.0
    """
    for attempt in range(max_retries):
        try:
            positions = grvt.fetch_positions(symbols=[symbol])
            if positions and len(positions) > 0:
                position = positions[0]
                size_str = position.get("size", "0")
                return float(size_str)
            return 0.0
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                # 只在最终失败时记录错误
                return 0.0
    return 0.0

def get_base_currency_from_pair(trading_pair: str) -> str:
    """从交易对中提取基础货币，例如 XPL-USDT -> XPL"""
    if "-" in trading_pair:
        return trading_pair.split("-")[0].strip()
    return trading_pair.strip()

def check_account_position(page, env_id: str, trading_pair: str, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[float]:
    """
    通过UI检查账户持仓（带重试机制）
    
    Args:
        page: Playwright页面对象
        env_id: 环境ID
        trading_pair: 交易对（如 "XPL-USDT"）
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    
    Returns:
        持仓数量，如果失败返回None
    """
    for attempt in range(max_retries):
        try:
            # 提取基础货币（如 "XPL-USDT" -> "XPL"）
            base_currency = get_base_currency_from_pair(trading_pair)
            
            # 点击仓位按钮（匹配 data-text 属性，可能包含数字如 "仓位（ 0 ）"）
            try:
                # 尝试精确匹配
                position_button = page.locator('div[data-text^="仓位"]').first
                if position_button.count() == 0:
                    # 如果精确匹配失败，尝试包含文本的匹配
                    position_button = page.locator('div:has-text("仓位")').first
                position_button.click(timeout=5000)
                time.sleep(1)  # 等待仓位列表加载
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"  [{env_id}] 检查持仓失败: {e}")
                    return None
            
            # 查找仓位列表中的所有行
            rows = page.locator('div.style_tableRow__gbjWO').all()
            
            # 遍历行，找到对应的交易对
            for row in rows:
                try:
                    # 查找交易对名称（在第一列的 div.fx-as-flex-start 中）
                    instrument_cell = row.locator('div.fx-as-flex-start.txt-hover-brand').first
                    if instrument_cell.count() == 0:
                        continue
                    
                    instrument_text = instrument_cell.inner_text(timeout=2000).strip()
                    
                    # 检查是否匹配基础货币
                    if instrument_text == base_currency:
                        # 找到对应的交易对，提取持仓数量
                        # 持仓数量在第二列，格式如 "30 XPL"
                        position_cells = row.locator('div.fx-column.fx-jc-center').all()
                        if len(position_cells) >= 2:
                            position_text = position_cells[1].inner_text(timeout=2000).strip()
                            # 提取数字部分（如 "30 XPL" -> 30）
                            match = re.search(r'([-]?\d+\.?\d*)', position_text)
                            if match:
                                position_value = float(match.group(1))
                                return position_value
                except Exception:
                    continue
            
            # 如果没有找到对应的交易对，返回0（可能没有持仓）
            return 0.0
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print(f"  [{env_id}] 检查持仓失败: {e}")
                return None
    return None

# 缓存 adapter 实例
_grvt_adapter = None

def get_grvt_adapter():
    """获取 GRVT adapter 实例（单例模式）"""
    global _grvt_adapter
    if _grvt_adapter is None:
        config = {
            "exchange_name": "grvt",
            "env": "prod"
        }
        _grvt_adapter = create_adapter(config)
        _grvt_adapter.connect()
    return _grvt_adapter

def get_best_prices(trading_pair: str, max_retries: int = 3, retry_delay: float = 1.0) -> Tuple[float | None, float | None]:
    """
    获取最佳买价和卖价（带重试机制）
    
    Args:
        trading_pair: 交易对
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    
    Returns:
        (最佳买价, 最佳卖价)，如果失败返回 (None, None)
    """
    for attempt in range(max_retries):
        try:
            symbol = convert_trading_pair_to_symbol(trading_pair)
            adapter = get_grvt_adapter()
            ticker = adapter.get_ticker(symbol)
            
            bid_price = ticker.get("bid_price")
            ask_price = ticker.get("ask_price")
            
            if bid_price is None or ask_price is None:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None, None
            
            return float(bid_price), float(ask_price)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                # 获取价格失败不记录日志，由调用方处理
                return None, None
    return None, None

# 加载配置
cfg = load_config()
ENV_IDS = cfg["env_ids"]
TARGET_URL = cfg["target_url"]
API_BASE_URL = cfg["api_base_url"]
API_TIMEOUT = cfg["api_timeout"]
API_CLOSE_TIMEOUT = cfg["api_close_timeout"]
PAGE_LOAD_TIMEOUT = cfg["page_load_timeout"]
WAIT_UNTIL = cfg["wait_until"]
DELAY_AFTER_BROWSER_START = cfg["delay_after_browser_start"]
DELAY_BETWEEN_PROFILES = cfg["delay_between_profiles"]
TRADING_PAIR = cfg.get("trading_pair")
PRICE_OFFSET = cfg.get("price_offset", 0.0001)
TRADING_AMOUNT = cfg.get("amount", 0.001)
POSITION_CHECK_INTERVAL = cfg.get("position_check_interval", 3)


def start_profile(env_id: str) -> Optional[str]:
    """启动浏览器配置文件，返回 CDP URL"""
    try:
        data = requests.post(f"{API_BASE_URL}/api/env/start", json={"envId": env_id}, timeout=API_TIMEOUT).json()
        if data.get("code") == 0:
            return f"http://127.0.0.1:{data['data']['debugPort']}"
    except Exception:
        pass
    return None


def open_page(cdp_url: str, target_url: str, playwright):
    """
    在浏览器中打开页面，返回 page 对象
    优先复用已存在的页面，减少重复打开。
    """
    browser = playwright.chromium.connect_over_cdp(cdp_url)
    
    # 复用已存在的页面（任意 context）
    for ctx in browser.contexts:
        for pg in ctx.pages:
            current_url = pg.url or ""
            if current_url.startswith(target_url) or target_url in current_url:
                try:
                    pg.bring_to_front()
                except Exception:
                    pass
                return pg
    
    # 没有可复用页面则创建
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.new_page()
    page.goto(target_url, wait_until=WAIT_UNTIL, timeout=PAGE_LOAD_TIMEOUT)
    return page

def click_element(page, text: str):
    """点击包含指定文本的元素"""
    try:
        page.click(f'div[data-text="{text}"]', timeout=5000)
        return True
    except Exception:
        return False

def fill_price_input(page, price: float):
    """在价格输入框中输入价格，返回实际输入的值"""
    try:
        input_selector = 'input[placeholder="价格"].text-field_input__csqr7'
        page.fill(input_selector, "", timeout=5000)
        price_str = f"{price:.4f}"
        page.fill(input_selector, price_str, timeout=5000)
        page.evaluate(f'document.querySelector(\'{input_selector}\')?.blur()')
        time.sleep(0.5)
        actual_value = page.input_value(input_selector, timeout=2000)
        return actual_value
    except Exception:
        return None

def fill_amount_input(page, amount: float):
    """在数量输入框中输入数量，返回实际输入的值"""
    try:
        input_selector = 'input[placeholder="数量"].text-field_input__csqr7'
        page.fill(input_selector, "", timeout=5000)
        amount_str = f"{amount:.6f}".rstrip('0').rstrip('.')
        page.fill(input_selector, amount_str, timeout=5000)
        page.evaluate(f'document.querySelector(\'{input_selector}\')?.blur()')
        time.sleep(0.5)
        actual_value = page.input_value(input_selector, timeout=2000)
        return actual_value
    except Exception:
        return None

def click_buy_button(page):
    """点击做多按钮（买入 / 做多）"""
    try:
        button_selector = 'button:has-text("买入 / 做多")'
        page.click(button_selector, timeout=5000)
        time.sleep(0.5)
        return True
    except Exception:
        return False

def click_sell_button(page):
    """点击做空按钮（卖出 / 做空）"""
    try:
        button_selector = 'button:has-text("卖出 / 做空")'
        page.click(button_selector, timeout=5000)
        time.sleep(0.5)
        return True
    except Exception:
        return False

def click_open_orders_button(page):
    """点击未成交订单按钮"""
    try:
        # 匹配 data-text 属性，可能包含数字如 "未成交订单（ 1 ）"
        open_orders_button = page.locator('div[data-text^="未成交订单"]').first
        if open_orders_button.count() == 0:
            # 如果精确匹配失败，尝试包含文本的匹配
            open_orders_button = page.locator('div:has-text("未成交订单")').first
        open_orders_button.click(timeout=5000)
        time.sleep(1)  # 等待订单列表加载
        return True
    except Exception:
        return False

def cancel_all_open_orders(page, env_id: str) -> bool:
    """
    取消所有未成交订单
    
    Args:
        page: Playwright页面对象
        env_id: 环境ID
    
    Returns:
        是否成功
    """
    try:
        # 点击未成交订单按钮
        if not click_open_orders_button(page):
            return False
        
        # 等待订单列表加载
        time.sleep(1)
        
        # 更精确地查找未成交订单表格中的取消按钮
        # 使用 data-sentry-source-file="row.tsx" 来确保只找到订单行中的取消按钮
        cancel_buttons = page.locator('button[data-sentry-source-file="row.tsx"]:has-text("取消")').all()
        canceled_count = 0
        
        for cancel_button in cancel_buttons:
            try:
                # 检查按钮是否可见和可点击
                if cancel_button.is_visible(timeout=1000):
                    cancel_button.click(timeout=3000)
                    canceled_count += 1
                    time.sleep(0.3)  # 每次点击后稍作等待
            except Exception:
                continue
        
        if canceled_count > 0:
            print(f"  [{env_id}] 已取消 {canceled_count} 个未成交订单")
        
        return True
    except Exception as e:
        print(f"  [{env_id}] 取消未成交订单失败: {e}")
        return False

def place_limit_order(page, env_id: str, side: str, trading_pair: str, price_offset: float, amount: float) -> bool:
    """
    下限价单
    
    Args:
        page: Playwright页面对象
        env_id: 环境ID
        side: "buy" 或 "sell"（做多或做空）
        trading_pair: 交易对
        price_offset: 价格偏移量
        amount: 交易数量
    
    Returns:
        是否成功
    """
    try:
        # 点击限价按钮
        if not click_element(page, "限价"):
            return False
        
        # 获取价格并输入
        best_bid, best_ask = get_best_prices(trading_pair)
        if not best_bid or not best_ask:
            return False
        
        # 根据side计算价格
        if side == "buy":
            price = best_bid + price_offset
        else:  # sell
            price = best_ask - price_offset
        
        actual_price = fill_price_input(page, price)
        if not actual_price:
            return False
        
        # 输入数量
        actual_amount = fill_amount_input(page, amount)
        if not actual_amount:
            return False
        
        # 点击做多或做空按钮
        if side == "buy":
            if click_buy_button(page):
                return True
        else:  # sell
            if click_sell_button(page):
                return True
        
        return False
    except Exception as e:
        print(f"  [{env_id}] 下限价单失败: {e}")
        return False

def place_market_order(page, env_id: str, side: str, amount: float) -> bool:
    """
    下市价单
    
    Args:
        page: Playwright页面对象
        env_id: 环境ID
        side: "buy" 或 "sell"（做多或做空）
        amount: 交易数量
    
    Returns:
        是否成功
    """
    try:
        # 点击市价按钮
        if not click_element(page, "市价"):
            return False
        
        # 输入数量
        actual_amount = fill_amount_input(page, amount)
        if not actual_amount:
            return False
        
        # 点击做多或做空按钮
        if side == "buy":
            if click_buy_button(page):
                return True
        else:  # sell
            if click_sell_button(page):
                return True
        
        return False
    except Exception as e:
        print(f"  [{env_id}] 下市价单失败: {e}")
        return False


def stop_profile(env_id: str, timeout: int = None):
    """关闭浏览器配置文件"""
    try:
        requests.post(
            f"{API_BASE_URL}/api/env/close",
            json={"envId": env_id},
            timeout=timeout or API_TIMEOUT
        )
    except Exception:
        pass


def check_api_connection() -> tuple[bool, str]:
    """检查 API 连接是否可用"""
    try:
        requests.post(f"{API_BASE_URL}/api/env/page", json={"pageNo": 1, "pageSize": 1}, timeout=2)
        return True, ""
    except requests.exceptions.ConnectionError:
        return False, f"无法连接到 {API_BASE_URL}，请确保 MoreLogin 客户端已启动"
    except requests.exceptions.Timeout:
        return False, f"连接超时"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"


def main():
    if not ENV_IDS:
        print("错误: 配置文件中没有环境ID")
        return
    
    if not TARGET_URL:
        print("错误: 未配置交易对或目标URL")
        return
    
    if len(ENV_IDS) < 2:
        print(f"错误: 至少需要2个环境ID，当前只有 {len(ENV_IDS)} 个")
        return
    
    is_connected, error_msg = check_api_connection()
    if not is_connected:
        print(f"错误: 无法连接到 MoreLogin API ({API_BASE_URL})")
        print(f"原因: {error_msg}")
        return
    
    print(f"打开 {len(ENV_IDS)} 个环境...")
    
    with sync_playwright() as playwright:
        opened_profiles = []
        profile_pages = {}  # 存储环境ID和对应的page对象
        
        for env_id in ENV_IDS:
            cdp_url = start_profile(env_id)
            if not cdp_url:
                continue
            
            time.sleep(DELAY_AFTER_BROWSER_START)
            
            try:
                page = open_page(cdp_url, TARGET_URL, playwright)
                opened_profiles.append(env_id)
                profile_pages[env_id] = page
                print(f"✓ {env_id}")
            except Exception:
                stop_profile(env_id)
            
            time.sleep(DELAY_BETWEEN_PROFILES)
        
        if opened_profiles:
            print(f"\n成功: {len(opened_profiles)}/{len(ENV_IDS)}")
            print("按 Ctrl+C 退出")
            
            try:
                loop_count = 0  # 循环计数器
                while True:
                    if len(opened_profiles) >= 2:
                        available = opened_profiles.copy()
                        first_id = random.choice(available)
                        print(f"1环境ID: [{first_id}]")
                        available.remove(first_id)
                        second_id = random.choice(available)
                        print(f"2环境ID: [{second_id}]")
                        
                        # 点击元素并操作
                        if first_id in profile_pages and TRADING_PAIR:
                            page1 = profile_pages[first_id]
                            # 下限价单做多
                            place_limit_order(page1, first_id, "buy", TRADING_PAIR, PRICE_OFFSET, TRADING_AMOUNT)
                        
                        if second_id in profile_pages:
                            page2 = profile_pages[second_id]
                            # 下市价单做空
                            place_market_order(page2, second_id, "sell", TRADING_AMOUNT)
                    if len(opened_profiles) >= 2 and TRADING_PAIR:
                        # 每N次循环检查一次持仓并处理
                        loop_count += 1
                        if loop_count % POSITION_CHECK_INTERVAL == 0:
                            print(f"\n=== 第 {loop_count // POSITION_CHECK_INTERVAL} 次持仓检查 ===")
                            
                            # 遍历 opened_profiles，实时获取持仓并处理
                            for i, env_id in enumerate(opened_profiles):
                                page = profile_pages.get(env_id)
                                if not page:
                                    continue
                                
                                # 获取持仓
                                position = check_account_position(page, env_id, TRADING_PAIR)
                                if position is None or abs(position) < 0.0001:
                                    continue
                                
                                print(f"  [{env_id}] 当前持仓: {position:.4f}")
                                
                                abs_position = abs(position)
                                is_last = (i == len(opened_profiles) - 1)
                                
                                if is_last:
                                    # 最后一个环境：取消未成交订单后限价平仓
                                    cancel_all_open_orders(page, env_id)
                                    time.sleep(1)
                                    
                                    side = "sell" if position > 0 else "buy"
                                    print(f"  [{env_id}] 最后环境，限价平仓: {'卖出' if position > 0 else '买入'} {abs_position:.4f}")
                                    place_limit_order(page, env_id, side, TRADING_PAIR, PRICE_OFFSET, abs_position)
                                else:
                                    # 非最后环境：当前环境限价单，下一个环境市价单
                                    next_env_id = opened_profiles[i + 1]
                                    next_page = profile_pages.get(next_env_id)
                                    if not next_page:
                                        continue
                                    
                                    if position > 0:
                                        # 持仓为正：当前限价空单，下一个市价多单
                                        print(f"  [{env_id}] 限价空单: {abs_position:.4f}")
                                        place_limit_order(page, env_id, "sell", TRADING_PAIR, PRICE_OFFSET, abs_position)
                                        print(f"  [{next_env_id}] 市价多单: {abs_position:.4f}")
                                        place_market_order(next_page, next_env_id, "buy", abs_position)
                                    else:
                                        # 持仓为负：当前限价多单，下一个市价空单
                                        print(f"  [{env_id}] 限价多单: {abs_position:.4f}")
                                        place_limit_order(page, env_id, "buy", TRADING_PAIR, PRICE_OFFSET, abs_position)
                                        print(f"  [{next_env_id}] 市价空单: {abs_position:.4f}")
                                        place_market_order(next_page, next_env_id, "sell", abs_position)
                                    
                                    time.sleep(1)
                    
                    time.sleep(10)
            except KeyboardInterrupt:
                print("\n关闭环境...")
                # for env_id in opened_profiles:
                #     stop_profile(env_id, timeout=API_CLOSE_TIMEOUT)
        else:
            print("没有成功打开任何环境")


if __name__ == "__main__":
    main()
