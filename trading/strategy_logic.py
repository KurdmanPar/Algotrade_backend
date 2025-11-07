# backend/trading/strategy_logic.py

import pandas as pd
import numpy as np


class BaseStrategy:
    """
    کلاس پایه برای تمام استراتژی‌های معاملاتی.
    هر استراتژی جدید باید از این کلاس ارث‌بری کرده و متد generate_signals را پیاده‌سازی کند.
    """

    def __init__(self, short_window=10, long_window=20):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        این متد باید در کلاس‌های فرزند بازنویسی شود.
        یک DataFrame از قیمت‌ها را دریافت کرده و یک DataFrame از سیگنال‌ها را برمی‌گرداند.
        """
        raise NotImplementedError("Subclasses must implement this method")


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    پیاده‌سازی استراتژی کراس اوور میانگین متحرک.
    - وقتی میانگین متحرک کوتاه‌مدت، میانگین متحرک بلندمدت را از پایین به بالا قطع کند، سیگنال خرید (Buy) صادر می‌شود.
    - وقتی میانگین متحرک کوتاه‌مدت، میانگین متحرک بلندمدت را از بالا به پایین قطع کند، سیگنال فروش (Sell) صادر می‌شود.
    """

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        سیگنال‌های معاملاتی را بر اساس داده‌های قیمت تولید می‌کند.

        Args:
            price_data (pd.DataFrame): DataFrame با ستون 'close' و index زمانی.

        Returns:
            pd.DataFrame: DataFrame با ستون 'signal' (1 برای خرید, -1 برای فروش, 0 برای نگه داشتن)
        """
        # محاسبه میانگین‌های متحرک
        price_data['short_mavg'] = price_data['close'].rolling(window=self.short_window, min_periods=1).mean()
        price_data['long_mavg'] = price_data['close'].rolling(window=self.long_window, min_periods=1).mean()

        # ایجاد سیگنال‌ها
        signals = pd.DataFrame(index=price_data.index)
        signals['signal'] = 0

        # سیگنال خرید: وقتی میانگین کوتاه‌مدت از بلندمدت عبور می‌کند
        signals['signal'][self.short_window:] = np.where(
            price_data['short_mavg'][self.short_window:] > price_data['long_mavg'][self.short_window:], 1, 0
        )

        # سیگنال فروش: وقتی میانگین کوتاه‌مدت از بلندمدت پایین‌تر می‌آید
        signals['signal'][self.short_window:] = np.where(
            price_data['short_mavg'][self.short_window:] < price_data['long_mavg'][self.short_window:], -1,
            signals['signal'][self.short_window:]
        )

        # پیدا کردن نقاطی که سیگنال تغییر می‌کند (از 0 به 1 یا از 1 به -1)
        signals['positions'] = signals['signal'].diff()

        # این خط بسیار مهم است: مقدار NaN اولیه را با 0 پر می‌کنیم
        signals['positions'].fillna(0, inplace=True)

        return signals