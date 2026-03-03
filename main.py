# main.py
import os
import akshare as ak
import requests
from dashscope import Generation

# 从环境变量读取密钥（GitHub Secrets 中配置）
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 自定义关注股票池（A股6位代码）
WATCHLIST = {
    "002138": "顺络电子",
    "601179": "中国西电",
    "601126": "四方股份"
}

def get_market_data():
    """获取大盘指数和热门板块"""
    try:
        sh = ak.stock_zh_index_spot_em(symbol="sh000001")["最新价"].iloc[0]
        sz = ak.stock_zh_index_spot_em(symbol="sz399001")["最新价"].iloc[0]
        sectors = ak.stock_sector_fund_flow_rank(indicator="今日")
        top_sectors = [f"{row['行业']}（{row['涨跌幅']:.2f}%）" for _, row in sectors.head(3).iterrows()]
        return {"indices": {"上证指数": sh, "深证成指": sz}, "top_sectors": top_sectors}
    except Exception as e:
        print("数据获取失败:", e)
        return {"indices": {}, "top_sectors": []}

def get_my_stocks():
    """获取自选股票最新行情"""
    stocks = []
    for code, name in WATCHLIST.items():
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", count=2)
            today, yesterday = df.iloc[-1], df.iloc[-2]
            change = (today["收盘"] - yesterday["收盘"]) / yesterday["收盘"] * 100
            stocks.append({"name": name, "price": today["收盘"], "change": change})
        except Exception as e:
            print(f"{name} 数据异常:", e)
            stocks.append({"name": name, "price": "N/A", "change": 0})
    return stocks

def generate_ai_summary(market, my_stocks):
    """调用 Qwen-Max 生成七维分析简报"""
    stock_str = "\n".join([f"- {s['name']}: {s['price']:.2f} ({s['change']:+.2f}%)" for s in my_stocks])
    sector_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(market["top_sectors"])])
    
    prompt = f"""
你是一位资深电力设备与电子元器件行业分析师，请基于以下最新市场数据，围绕【顺络电子（002138）】【中国西电（601179）】【四方股份（601126）】三只股票，生成一份结构清晰、专业简洁的晚间策略简报。

要求：
- 语言精炼，总字数控制在 200 字以内
- 每个板块用「一、二、…」编号，不可省略
- 不编造数据，仅基于提供信息推理

【指数结构】
上证: {market['indices'].get('上证指数', 'N/A')}
深证: {market['indices'].get('深证成指', 'N/A')}

【资金结构】
热门板块前三：
{sector_str}

【政策扫描】
近期无新增重大产业政策（默认）

【行业高频】
- 电力设备/电子元件板块今日整体表现活跃

【持仓专项分析】
{stock_str}

请按以下七点输出：
一、指数结构  
二、资金结构  
三、政策扫描  
四、行业高频  
五、持仓专项分析  
六、技术形态判断  
七、明日操作建议
"""

    resp = Generation.call(
        model="qwen-max",
        api_key=DASHSCOPE_API_KEY,
        prompt=prompt,
        temperature=0.3  # 降低随机性，更稳定
    )
    return resp.output.text.strip() if resp.status_code == 200 else "AI 分析暂不可用。"

def send_feishu(msg):
    """推送消息到飞书群"""
    full_msg = "【AI A股晚报 · 电力设备专题】\n" + msg
    payload = {"msg_type": "text", "content": {"text": full_msg}}
    try:
        r = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=10)
        if r.json().get("StatusCode") == 0:
            print("✅ 飞书推送成功")
        else:
            print("❌ 推送失败:", r.text)
    except Exception as e:
        print("💥 飞书异常:", e)

def main():
    print("🚀 开始生成电力设备专题 A 股晚报...")
    market = get_market_data()
    my_stocks = get_my_stocks()
    ai_summary = generate_ai_summary(market, my_stocks)

    # 构建预览文本（用于日志）
    preview = "【AI A股晚报 · 电力设备专题】\n\n"
    preview += "📈 大盘\n"
    for k, v in market["indices"].items():
        preview += f"- {k}: {v}\n"
    preview += "\n🔥 热门板块\n" + "\n".join(f"- {s}" for s in market["top_sectors"])
    preview += "\n\n💼 我的持仓\n"
    for s in my_stocks:
        sign = "✅" if s["change"] > 0 else "⚠️"
        preview += f"{sign} {s['name']}: {s['price']:.2f} ({s['change']:+.2f}%)\n"
    preview += f"\n🧠 AI策略\n{ai_summary}"

    print("\n--- 预览 ---\n", preview)
    send_feishu(ai_summary)  # 只推送 AI 总结部分（更简洁）

if __name__ == "__main__":
    main()
