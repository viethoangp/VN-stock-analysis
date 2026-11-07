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


def _self_test():
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
