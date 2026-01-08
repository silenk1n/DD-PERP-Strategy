"""
GRVT Exchange Adapter Implementation

This module implements BasePerpAdapter for GRVT exchange.
"""
import sys
import os
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from adapters.base_adapter import BasePerpAdapter, Balance, Position, Order

# 导入 GRVT 相关模块
# 注意：目录名包含 '-' 字符，需要添加到 sys.path 后直接导入模块名
grvt_sdk_path = os.path.join(project_root, 'exchange', 'exchange_grvt', 'grvt-pysdk-main', 'src')
if grvt_sdk_path not in sys.path:
    sys.path.insert(0, grvt_sdk_path)

from pysdk.grvt_ccxt import GrvtCcxt
from pysdk.grvt_ccxt_env import GrvtEnv


class GrvtAdapter(BasePerpAdapter):
    """GRVT 交易所适配器实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 GRVT 适配器
        
        Args:
            config: 配置字典，必须包含：
                - exchange_name: "grvt"
                - env: 环境名称，如 "prod", "testnet"（可选，默认 "prod"）
        """
        super().__init__(config)
        env_str = config.get("env", "prod").lower()
        env_map = {
            "prod": GrvtEnv.PROD,
            "testnet": GrvtEnv.TESTNET,
            "staging": GrvtEnv.STAGING,
            "dev": GrvtEnv.DEV,
        }
        self.env = env_map.get(env_str, GrvtEnv.PROD)
        
        # 初始化 GRVT 客户端（获取价格不需要认证）
        self.grvt_client = GrvtCcxt(env=self.env)
    
    def connect(self) -> bool:
        """
        连接到 GRVT（获取价格不需要认证，直接返回成功）
        
        Returns:
            bool: 连接是否成功
        """
        return True
    
    def get_balance(self) -> Balance:
        """查询账户余额"""
        raise NotImplementedError("GRVT 余额查询功能待实现")
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """查询持仓信息"""
        raise NotImplementedError("GRVT 持仓查询功能待实现")
    
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        time_in_force: str = "gtc",
        reduce_only: bool = False,
        client_order_id: Optional[str] = None,
        **kwargs
    ) -> Order:
        """下单"""
        raise NotImplementedError("GRVT 下单功能待实现")
    
    def cancel_order(
        self,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> bool:
        """撤单"""
        raise NotImplementedError("GRVT 撤单功能待实现")
    
    def cancel_all_orders(
        self,
        symbol: Optional[str] = None,
    ) -> bool:
        """撤销所有订单"""
        raise NotImplementedError("GRVT 批量撤单功能待实现")
    
    def get_order(
        self,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> Optional[Order]:
        """查询订单状态"""
        raise NotImplementedError("GRVT 订单查询功能待实现")
    
    def get_open_orders(
        self,
        symbol: Optional[str] = None,
    ) -> List[Order]:
        """查询所有未成交订单"""
        raise NotImplementedError("GRVT 未成交订单查询功能待实现")
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取交易对的最新价格信息
        
        Args:
            symbol: 交易对符号，如 "BTC_USDT_Perp"
            
        Returns:
            Dict[str, Any]: 包含最新价、买一价、卖一价等信息
        """
        try:
            ticker_data = self.grvt_client.fetch_ticker(symbol)
            
            # 处理返回的数据结构（可能是列表或字典）
            if isinstance(ticker_data, list) and len(ticker_data) > 0:
                ticker_data = ticker_data[0]
            elif isinstance(ticker_data, list) and len(ticker_data) == 0:
                raise Exception(f"未找到交易对 {symbol} 的价格数据")
            
            if not isinstance(ticker_data, dict):
                raise Exception(f"返回的数据格式不正确: {type(ticker_data)}")
            
            # 转换价格（根据 GRVT API 文档，fetch_ticker 返回的价格已经是实际价格，不需要除以 PRICE_MULTIPLIER）
            def parse_price(price_str: Optional[str]) -> Optional[float]:
                if not price_str or price_str == "0":
                    return None
                try:
                    return float(price_str)
                except (ValueError, TypeError):
                    return None
            
            return {
                "symbol": ticker_data.get("instrument", symbol),
                "bid_price": parse_price(ticker_data.get("best_bid_price")),
                "ask_price": parse_price(ticker_data.get("best_ask_price")),
                "mid_price": parse_price(ticker_data.get("mid_price")),
                "last_price": parse_price(ticker_data.get("last_price")),
                "mark_price": parse_price(ticker_data.get("mark_price")),
                "index_price": parse_price(ticker_data.get("index_price")),
                "timestamp": int(time.time() * 1000),
            }
        except Exception as e:
            raise Exception(f"获取价格失败: {e}")
    
    def get_orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> Dict[str, Any]:
        """获取订单簿"""
        raise NotImplementedError("GRVT 订单簿查询功能待实现")
