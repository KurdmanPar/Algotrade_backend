
# backend/trading/tests/test_strategy_logic.py

"""
این تست یک سناریوی مشخص را شبیه‌سازی می‌کند:
ابتدا یک روند صعودی (که باید سیگنال خرید بدهد) و
سپس یک روند نزولی (که باید سیگنال فروش بدهد).
"""


import pytest
import pandas as pd
import numpy as np
from trading.strategy_logic import MovingAverageCrossoverStrategy

def test_moving_average_crossover_strategy():
    """
    تست منطق استراتژی کراس اوور میانگین متحرک.
    این تست داده‌های قیمتی ساختگی را ایجاد می‌کند و سیگنال‌های خرید و فروش تولید شده را بررسی می‌کند.
    """
    # 1. Arrange (آماده‌سازی)
    # ایجاد داده‌های قیمتی ساختگی
    # - روزهای 0 تا 9: قیمت‌ها نوسان دارند اما روند خاصی ندارند
    # - روزهای 10 تا 19: یک روند صعودی قوی (برای تولید سیگنال خرید)
    # - روزهای 20 تا 29: یک روند نزولی قوی (برای تولید سیگنال فروش)
    price_data = pd.DataFrame(
        data={
            'close': [100, 101, 99, 102, 98, 103, 105, 104, 106, 107,  # نوسان
                      110, 112, 115, 118, 120, 125, 128, 130, 132, 135,  # صعودی
                      133, 130, 125, 120, 115, 110, 105, 100, 95, 90]   # نزولی
        },
        index=pd.date_range(start='2023-01-01', periods=30, freq='D')
    )

    # مقداردهی پنجره‌های زمانی کوتاه و بلند
    short_window = 5
    long_window = 10

    strategy = MovingAverageCrossoverStrategy(short_window=short_window, long_window=long_window)



    # 2. Act (اجرا)
    # تولید سیگنال‌ها بر اساس داده‌های قیمتی
    signals = strategy.generate_signals(price_data)







    # 3. Assert (بررسی)
    # بررسی می‌کنیم که خروجی یک DataFrame است و ستون‌های مورد نظر را دارد
    assert isinstance(signals, pd.DataFrame)
    assert 'signal' in signals.columns
    assert 'positions' in signals.columns

    # پیدا کردن نقاطی که سیگنال تغییر می‌کند (موقعیت‌های خرید و فروش)
    buy_signals = signals[signals['positions'] > 0]
    sell_signals = signals[signals['positions'] < 0]

    # انتظار داریم که یک سیگنال خرید و یک سیگنال فروش داشته باشیم
    assert len(buy_signals) == 1, "Should have exactly one buy signal"
    assert len(sell_signals) == 1, "Should have exactly one sell signal"

    # بررسی می‌کنیم که ترتیب سیگنال‌ها صحیح است
    buy_signal_date = buy_signals.index[0]
    sell_signal_date = sell_signals.index[0]

    # منطق اصلی تست: سیگنال خرید باید قبل از سیگنال فروش رخ دهد
    assert buy_signal_date < sell_signal_date, "Buy signal must occur before sell signal"

    # بررسی می‌کنیم که سیگنال خرید در اوایل دوره داده‌ها رخ داده است
    # (قبل از شروع روند نزولی که در روز 20 شروع می‌شود)
    assert buy_signal_date < pd.to_datetime('2023-01-20'), "Buy signal should occur before the downtrend starts"

    # بررسی می‌کنیم که سیگنال فروش در اواخر دوره داده‌ها رخ داده است
    # (بعد از شروع روند نزولی)
    assert sell_signal_date > pd.to_datetime('2023-01-20'), "Sell signal should occur after the downtrend starts"

    # بررسی مقادیر سیگنال‌ها
    assert buy_signals['positions'].iloc[0] == 1.0
    assert sell_signals['positions'].iloc[0] == -2.0

    # برای دیباگ کردن، می‌توانیم تاریخ‌های واقعی را چاپ کنیم
    print(f"Actual Buy Signal Date: {buy_signal_date.date()}")
    print(f"Actual Sell Signal Date: {sell_signal_date.date()}")
