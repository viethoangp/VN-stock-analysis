"""Chỉ số lợi suất và rủi ro (công thức: docs/project_plan.md mục 9).

Đầu vào là chuỗi giá đóng cửa đã điều chỉnh (pd.Series, index = ngày). Lợi suất là số thập phân (0.05 = 5%).
Chạy `python src/metrics.py` để tự kiểm tra trên dữ liệu giả có đáp án biết trước.
"""
import numpy as np
import pandas as pd

from config import RISK_FREE_RATE, TRADING_DAYS_PER_YEAR as N

MIN_SESSION_SHARE = 0.8  # mã–năm có ít hơn 80% số phiên VN-Index thì bỏ (xem 01_data_quality)


def daily_returns(close):
    return close.pct_change().dropna()


def annualized_return(close):
    """(P_cuối / P_đầu)^(252/n) − 1, n = số phiên lợi suất."""
    n = len(close) - 1
    return (close.iloc[-1] / close.iloc[0]) ** (N / n) - 1


def annualized_volatility(r):
    return r.std() * np.sqrt(N)


def max_drawdown(close):
    """Mức sụt sâu nhất từ đỉnh: trả (giá trị âm, ngày đỉnh, ngày đáy)."""
    dd = close / close.cummax() - 1
    trough = dd.idxmin()
    peak = close.loc[:trough].idxmax()
    return dd.min(), peak, trough


def sharpe(close, rf=RISK_FREE_RATE):
    return (annualized_return(close) - rf) / annualized_volatility(daily_returns(close))


def beta(r_stock, r_index):
    """cov(r_mã, r_chỉ số) / var(r_chỉ số), chỉ trên các ngày cả hai cùng có."""
    df = pd.concat([r_stock, r_index], axis=1, join="inner").dropna()
    return df.iloc[:, 0].cov(df.iloc[:, 1]) / df.iloc[:, 1].var()


def yearly_metrics(prices, index_close, rf=RISK_FREE_RATE):
    """Chỉ số theo mã × năm.

    prices: DataFrame (ticker, date, close); index_close: chuỗi giá VN-Index.
    Lợi suất năm tính từ giá đóng cửa cuối năm trước (nếu có) để không bỏ sót phiên đầu năm.
    Bỏ mã–năm có ít hơn MIN_SESSION_SHARE số phiên của VN-Index.
    """
    index_close = index_close.copy()
    index_close.index = pd.to_datetime(index_close.index)
    r_index = daily_returns(index_close)
    index_sessions = index_close.groupby(index_close.index.year).size()
    rows = []
    for t, g in prices.groupby("ticker"):
        close = g.set_index(pd.to_datetime(g.date)).close.sort_index()
        r = daily_returns(close)
        for y, ry in r.groupby(r.index.year):
            sessions = (close.index.year == y).sum()
            if sessions < MIN_SESSION_SHARE * index_sessions[y]:
                continue
            c = close.loc[:str(y)].iloc[-(len(ry) + 1):]  # giá cuối năm trước + các phiên trong năm
            total = c.iloc[-1] / c.iloc[0] - 1
            ann = (1 + total) ** (N / len(ry)) - 1
            vol = annualized_volatility(ry)
            rows.append({
                "ticker": t, "year": y, "sessions": sessions, "total_return": total,
                "annualized_return": ann, "volatility": vol, "sharpe": (ann - rf) / vol,
                "max_drawdown": max_drawdown(c)[0], "beta": beta(ry, r_index),
            })
    return pd.DataFrame(rows)


def turning_points(close, threshold=0.15):
    """Đỉnh/đáy: xu hướng đổi chiều khi giá đi ngược >= threshold từ cực trị gần nhất.

    Trả danh sách ngày gồm ngày đầu, các đỉnh/đáy đã xác nhận, ngày cuối.
    """
    pivots, trend = [close.index[0]], None
    hi = lo = close.index[0]
    for d, x in close.items():
        if trend != "down" and x > close[hi]:
            hi = d
        if trend != "up" and x < close[lo]:
            lo = d
        if trend != "down" and x <= close[hi] * (1 - threshold):
            if hi != pivots[-1]:
                pivots.append(hi)
            trend, lo = "down", d
        elif trend != "up" and x >= close[lo] * (1 + threshold):
            if lo != pivots[-1]:
                pivots.append(lo)
            trend, hi = "up", d
    if close.index[-1] != pivots[-1]:
        pivots.append(close.index[-1])
    return pivots


def market_regimes(close, threshold=0.15, flat_below=0.25):
    """Chia giai đoạn theo đỉnh/đáy: đoạn đi xuống = Giảm; đoạn đi lên có lợi suất năm hóa
    > flat_below = Tăng, còn lại = Đi ngang. Đoạn đầu/cuối chưa đủ threshold để xác nhận xu hướng
    cũng là Đi ngang. Nhãn mô tả nhìn lại, KHÔNG dùng làm đặc trưng dự đoán.

    Trả (bảng các đoạn, nhãn theo từng ngày).
    """
    p = turning_points(close, threshold)
    segs = []
    for a, b in zip(p, p[1:]):
        n = close.index.get_loc(b) - close.index.get_loc(a)
        change = close[b] / close[a] - 1
        ann = (1 + change) ** (N / n) - 1
        if abs(change) < threshold or 0 <= ann <= flat_below:
            label = "Đi ngang"
        else:
            label = "Giảm" if change < 0 else "Tăng"
        segs.append({"start": a, "end": b, "sessions": n, "change": change, "annualized": ann, "regime": label})
    segs = pd.DataFrame(segs)
    labels = pd.Series(index=close.index, dtype=object)
    for s in segs.itertuples():
        labels.loc[s.start:s.end] = s.regime  # ngày đỉnh/đáy thuộc đoạn sau (gán đè)
    return segs, labels


def _self_test():
    # Giai đoạn: lên 30% -> xuống 20% -> lên 25%, có nhiễu nhỏ hơn ngưỡng
    path = np.concatenate([np.linspace(100, 130, 60), np.linspace(130, 104, 40), np.linspace(104, 130, 60)])
    path = path * (1 + 0.01 * np.sin(np.arange(160)))
    c = pd.Series(path, index=pd.bdate_range("2021-01-01", periods=160))
    segs, lab = market_regimes(c)
    assert list(segs.regime) == ["Tăng", "Giảm", "Tăng"], segs
    assert lab.notna().all()
    # Bắt đầu bằng xu hướng giảm
    segs, _ = market_regimes(pd.Series(path[::-1], index=c.index))
    assert list(segs.regime) == ["Giảm", "Tăng", "Giảm"], segs
    # Đi lên chậm (25% trong 2 năm) và dao động dưới ngưỡng -> Đi ngang
    slow = pd.Series(np.linspace(100, 125, 504), index=pd.bdate_range("2021-01-01", periods=504))
    assert list(market_regimes(slow)[0].regime) == ["Đi ngang"]
    assert list(market_regimes(slow.iloc[:100] * 0 + 100 + np.sin(np.arange(100)))[0].regime) == ["Đi ngang"]


    days = pd.bdate_range("2021-01-01", periods=253)
    up = pd.Series(100 * 1.01 ** np.arange(253), index=days)
    assert np.allclose(daily_returns(up), 0.01)
    assert abs(annualized_volatility(daily_returns(up))) < 1e-12
    assert abs(annualized_return(up) - (1.01 ** 252 - 1)) < 1e-9

    s = pd.Series([100, 120, 90, 110], index=days[:4])
    mdd, peak, trough = max_drawdown(s)
    assert abs(mdd + 0.25) < 1e-12 and peak == days[1] and trough == days[2]

    rng = np.random.default_rng(0)
    r_idx = pd.Series(rng.normal(0, 0.01, 252), index=days[1:])
    assert abs(beta(2 * r_idx, r_idx) - 2) < 1e-9
    assert abs(beta(r_idx.iloc[10:], r_idx) - 1) < 1e-9  # chỉ ghép ngày chung

    # Năm dương lịch: giá đóng cửa cuối 2021 = 100, cuối 2022 = 150 -> lợi suất 2022 = 50%
    d = pd.bdate_range("2021-01-04", "2022-12-30")
    idx = pd.Series(np.linspace(100, 150, len(d)), index=d)
    px = pd.DataFrame({"ticker": "X", "date": d, "close": idx.values})
    m = yearly_metrics(px, idx).set_index("year")
    end21 = idx.loc["2021"].iloc[-1]
    assert abs(m.loc[2022, "total_return"] - (150 / end21 - 1)) < 1e-9
    assert abs(m.loc[2022, "beta"] - 1) < 1e-6
    assert len(yearly_metrics(px[px.date >= "2022-11-01"], idx)) == 0  # quá ít phiên -> bị bỏ
    print("metrics: mọi kiểm tra đều qua")


if __name__ == "__main__":
    _self_test()
