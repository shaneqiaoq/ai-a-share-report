# main.py
import os
import akshare as ak
import requests
import pandas as pd
from dashscope import Generation
import textwrap  # 👈 必须加！否则报错

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
    """获取大盘指数、资金流热门板块、涨幅榜、跌幅榜"""
    try:
        # 大盘指数
        sh_df = ak.stock_zh_index_spot_em(symbol="sh000001")
        sz_df = ak.stock_zh_index_spot_em(symbol="sz399001")
        
        # 安全取值：防止空DataFrame
        sh = float(sh_df["最新价"].iloc[0]) if not sh_df.empty else "N/A"
        sz = float(sz_df["最新价"].iloc[0]) if not sz_df.empty else "N/A"

        # 资金流热门板块
        fund_flow_sectors = ak.stock_sector_fund_flow_rank(indicator="今日")
        top_fund_sectors = []
        for _, row in fund_flow_sectors.head(3).iterrows():
            sector_name = row['行业']
            change_pct = float(row['涨跌幅'])
            top_fund_sectors.append(f"{sector_name}（{change_pct:.2f}%）")

        # 所有板块涨跌幅数据
        all_sectors = ak.stock_sector_spot_em()
        all_sectors["涨跌幅"] = pd.to_numeric(all_sectors["涨跌幅"], errors="coerce")
        all_sectors = all_sectors.dropna(subset=["涨跌幅"])

        # 涨幅最大前三
        gain_list = []
        if len(all_sectors) > 0:
            top_gain = all_sectors.nlargest(3, "涨跌幅")[["板块名称", "涨跌幅"]]
            gain_list = [f"{row['板块名称']}（{row['涨跌幅']:.2f}%）" for _, row in top_gain.iterrows()]

        # 跌幅最大前三
        loss_list = []
        if len(all_sectors) > 0:
            top_loss = all_sectors.nsmallest(3, "涨跌幅")[["板块名称", "涨跌幅"]]
            loss_list = [f"{row['板块名称']}（{row['着跌']:.2f}%）" for _, row in top_loss.iterrows()]

        return {
            "indices": {"上证指数": sh, "深证成指": sz},
            "top_fund_sectors": top_fund_sectors,
            "top_gain_sectors": gain_list,
            "top_loss_sectors": loss_list
        }
    except Exception as e:
        print("数据获取失败:", e)
        return {
            "indices": {},
            "top_fund_sectors": [],
            "top_gain_sectors": [],
            "top_loss_sectors": []
        }

def get_my_stocks():
    stocks = []
    for code, name in WATCHLIST.items():
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", limit=2)
            if len(df) < 2:
                raise ValueError("历史数据不足")
            today = df.iloc[-1]
            yesterday = df.iloc[-2]
            
            # 确保字段存在
            if "收盘" not in today or "收盘" not in yesterday:
                raise ValueError("缺少'收盘'字段")
            close_today = float(today["收盘"])
            close_yest = float(yesterday["收盘"])
            change = (close_today - close_yest) / close_yest * 100
            stocks.append({"name": name, "price": close_today, "change": change})
        except Exception as e:
            print(f"{name} 数据异常:", e)
            stocks.append({"name": name, "price": None, "change": 0.0})
    return stocks

def generate_ai_summary(market, my_stocks):
    """调用 Qwen-Max 生成七维分析简报"""
    stock_lines = []
    for s in my_stocks:
        if s["price"] is not None:
            line = f"- {s['name']}: {s['price']:.2f} ({s['change']:+.2f}%)"
        else:
            line = f"- {s['name']}: N/A"
        stock_lines.append(line)
    stock_str = "\n".join(stock_lines)

    fund_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(market["top_fund_sectors"])])
    gain_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(market["top_gain_sectors"])])
    loss_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(market["top_loss_sectors"])])
    
    prompt = textwrap.dedent(f"""
        你是一位资深电力设备与电子元器件行业分析师，请基于以下最新市场数据，围绕【顺络电子（002138）】【中国西电（601179）】【四方股份（601126）】三只股票，生成一份结构清晰、专业简洁的晚间策略简报。

        注意：部分数据可能因接口延迟或未更新而缺失，请根据已有信息进行合理推断，不要编造。

        要求：
        - 语言精炼，总字数控制在 250 字以内
        - 每个板块用「一、二、…」编号，不可省略
        - 不编造数据，仅基于提供信息推理

        【指数结构】
        上证: {market['indices'].get('上证指数', 'N/A')}
        深证: {market['indices'].get('深证成指', 'N/A')}

        【资金结构】（主力资金流入前3）
        {fund_str}

        【涨幅榜】（全市场板块涨幅前三）
        {gain_str}

        【跌幅榜】（全市场板块跌幅前三）
        {loss_str}

        【政策扫描】
        近期无新增重大产业政策影响该行业，维持现有策略不变。

        【行业高频】
        - 电力设备/电子元件板块今日整体表现活跃

        【持仓专项分析】
        {stock_str}

        请按以下七点输出：
        一、指数结构  
        二、资金结构  
        三、涨幅与跌幅板块异动  
        四、政策扫描  
        五、行业高频  
        六、持仓专项分析  
        七、明日操作建议
    """).strip()

    resp = Generation.call(
        model="qwen-max",
        api_key=DASHSCOPE_API_KEY,
        prompt=prompt,
        temperature=0.3
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
    
    preview += "\n🔥 资金流热门板块\n" + "\n".join(f"- {s}" for s in market["top_fund_sectors"])
    preview += "\n\n🟢 涨幅最大板块\n" + "\n".join(f"- {s}" for s in market["top_gain_sectors"])
    preview += "\n\n🔴 跌幅最大板块\n" + "\n".join(f"- {s}" for s in market["top_loss_sectors"])
    
    preview += "\n\n💼 我的持仓\n"
    for s in my_stocks:
        if s["price"] is not None:
            sign = "✅" if s["change"] > 0 else "⚠️"
            preview += f"{sign} {s['name']}: {s['price']:.2f} ({s['change']:+.2f}%)\n"
        else:
            preview += f"⚠️ {s['name']}: N/A\n"
    
    preview += f"\n🧠 AI策略\n{ai_summary}"

    print("\n--- 预览 ---\n", preview)
    send_feishu(ai_summary)

if __name__ == "__main__":
    main()
