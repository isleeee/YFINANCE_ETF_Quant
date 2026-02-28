import yfinance as yf
import pandas as pd
import datetime
import requests
import os

# ================= 配置区域 =================
SC_KEY = os.environ.get('SC_KEY') 

# 监控标的池 (雅虎财经格式：上海.SS, 深圳.SZ)
ETF_POOL = {
    "512100.SS": "中证1000ETF",
    "588000.SS": "科创50ETF",
    "513100.SS": "纳指100ETF",
    "513500.SS": "标普500ETF",
    "513330.SS": "恒生互联网ETF",
    "510300.SS": "沪深300ETF",
    "510500.SS": "中证500ETF",
    "159941.SZ": "纳指ETF"
}

MA_DAYS = 20
MOMENTUM_DAYS = 20
# ===========================================

def get_signal(symbol, name):
    try:
        # 下载最近 60 天的数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d")
        
        if df.empty or len(df) < MA_DAYS:
            return None

        # 计算指标
        curr_price = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(window=MA_DAYS).mean().iloc[-1]
        price_20d_ago = df['Close'].iloc[-MOMENTUM_DAYS-1]
        
        momentum = (curr_price - price_20d_ago) / price_20d_ago * 100
        safety_buffer = (curr_price - ma20) / ma20 * 100
        
        # 信号逻辑
        if curr_price <= ma20:
            signal = "🔴 破位"
        elif safety_buffer < 1.0:
            signal = "🟡 警戒"
        elif 1.0 <= safety_buffer < 5.0:
            signal = "🔵 正常"
        else:
            signal = "🟢 安全"

        return {
            "name": name, "code": symbol.split('.')[0],
            "price": round(curr_price, 3), "ma20": round(ma20, 3),
            "momentum": momentum, "safety": safety_buffer, "signal": signal
        }
    except Exception as e:
        print(f"读取 {name} 出错: {e}")
        return None

def main():
    results = []
    for sym, name in ETF_POOL.items():
        data = get_signal(sym, name)
        if data: results.append(data)

    if not results: return

    # 排序：动量降序
    results.sort(key=lambda x: x['momentum'], reverse=True)
    
    # 决策逻辑
    best = next((r for r in results if r['momentum'] > 0 and r['signal'] != "🔴 破位"), None)
    advice = f"🎯 建议持仓：【{best['name']}】" if best else "💤 建议操作：【全仓空仓】"

    # 构造推送
    content = f"### {advice}\n\n| 标的 | 20日涨幅 | 安全垫 | MA20参考 | 信号 |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for r in results:
        content += f"| {r['name']} | {r['momentum']:.2f}% | {r['safety']:.1f}% | **{r['ma20']}** | {r['signal']} |\n"
    
    content += f"\n更新时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(content)
    if SC_KEY:
        requests.post(f"https://sctapi.ftqq.com/{SC_KEY}.send", data={"title": f"策略指令：{advice}", "desp": content})

if __name__ == "__main__":
    main()
