# DD Strategy Bot

多平台永续合约（Perp）策略系统

## 📖 项目简介

DD Strategy Bot 是一个免费开源的多平台永续合约策略系统，支持多个交易所的统一接口，方便策略开发和部署。

## 👤 作者

**Twitter:** [@ddazmon](https://twitter.com/ddazmon)

## 📜 开源协议

本项目免费开源，欢迎使用和贡献。**使用本项目时，请务必标明作者 Twitter: @ddazmon**

## 🎯 功能特性

- ✅ 统一的适配器接口，支持多交易所
- ✅ 网格交易策略
- ✅ 自动撤单和下单
- ✅ 持仓管理和自动平仓
- ✅ 可配置的策略参数
- ✅ 支持 StandX、GRVT、VAR 等多个平台
- ✅ 技术指标计算（ADX 等）

## 📦 安装依赖

### 基础依赖

```bash
pip install -r requirements.txt
```

### TA-Lib 安装说明

**注意**：TA-Lib 需要先安装系统级依赖，然后才能通过 pip 安装 Python 包。

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install ta-lib
pip install TA-Lib
```

**macOS:**
```bash
brew install ta-lib
pip install TA-Lib
```

**Windows:**
```bash
# 方法1: 下载预编译的 wheel 文件
# 访问 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 下载对应 Python 版本的 .whl 文件，然后安装：
pip install TA_Lib-0.4.28-cp39-cp39-win_amd64.whl

# 方法2: 使用 conda
conda install -c conda-forge ta-lib
```

如果遇到安装问题，请参考 [TA-Lib 官方文档](https://ta-lib.org/install/)。

## 🔗 交易所邀请链接

使用以下邀请链接注册，可获得返佣优惠：

### StandX
- **返佣比例：** 5%
- **邀请链接：** https://standx.com/referral?code=Dazmon88

### GRVT
- **返佣比例：** 35%
- **邀请链接：** https://grvt.io/?ref=Dazmon

### VAR
- **返佣优惠：** 点差全返
- **邀请链接：** https://omni.variational.io/?ref=OMNINU3G7KVK

## ⚠️ 风险提示

- 本策略仅供学习和研究使用
- 加密货币交易存在高风险，可能导致资金损失
- 使用前请充分了解策略逻辑和风险
- 建议在测试环境充分测试后再使用真实资金
- 作者不对使用本策略造成的任何损失负责

## 📝 许可证

本项目采用开源许可证，免费使用。使用本项目时，请标明作者 Twitter: **@ddazmon**

## 📧 联系方式

如有问题或建议，请通过 Twitter 联系：[@ddazmon](https://twitter.com/ddazmon)

---

**免责声明：** 本软件仅供学习和研究使用。使用本软件进行交易的所有风险由使用者自行承担。作者不对任何交易损失负责。
