# Pine Script vs Python Bot - Logic Comparison

## SL Logic Analysis

### Pine Script (User's Code):

1. **SL Price Calculation (at entry time):**
```pine
center = (lastORB.h + lastORB.l) / 2.0
if slMethod == 'Balanced'
    lastORB.slPrice := center
```

2. **SL Trigger Check:**
```pine
// Stop Loss
if bar_index > lastORB.entryIndex and not na(lastORB.slPrice) and na(lastORB.slIndex) and 
   (lastORB.entryBullish and low < lastORB.slPrice or not lastORB.entryBullish and high > lastORB.slPrice)
    if not(bar_index == lastORB.tp1Index)
        lastORB.slFoundTick := true
        lastORB.slIndex := bar_index
```

**Key Points:**
- For LONG: SL triggers when `low < slPrice` (wick touches SL level)
- For SHORT: SL triggers when `high > slPrice` (wick touches SL level)
- Uses `<` and `>` (STRICT, not `<=` and `>=`)

### Python Bot (orb_algo.py):
```python
if is_long and low <= sl_price:  # Uses <=
    entry_data = None
elif not is_long and high >= sl_price:  # Uses >=
```

**DIFFERENCE #1:** Pine uses `<` / `>` but Python uses `<=` / `>=`

---

## "Failed Breakout = Stop" Logic?

### Pine Script Analysis:

The "Failed Breakout" only applies **BEFORE** entry is taken:
```pine
if lastORB.state == 'In Breakout'
    // Failed Breakout
    if curBreakout.isBullish and close < lastORB.h or not curBreakout.isBullish and close > lastORB.l
        curBreakout.failed := true
        curBreakout.endIndex := bar_index
        lastORB.state := 'Waiting For Breakouts'
```

**AFTER entry is taken (state = 'Entry Taken'):**
- There is NO "close < ORB High = stop" logic
- Only the calculated SL price (center for Balanced) is checked

**Answer: NO, Pine Script does NOT stop a long position just because price goes below ORB High after entry.**

---

## TP1 Logic Analysis

### Pine Script:
```pine
isProfitable = lastORB.entryBullish and ema > lastORB.entryPrice or 
               not lastORB.entryBullish and ema < lastORB.entryPrice

if bar_index > lastORB.entryIndex + 1 and isProfitable and 
   diffPercent(ema, lastORB.entryPrice) >= minimumProfitPercent
    if na(lastORB.slIndex) and na(lastORB.tp1Index) and 
       (lastORB.entryBullish and close < ema or not lastORB.entryBullish and close > ema)
        // TP1 triggered
```

**Key Points:**
- `isProfitable` uses **EMA > entryPrice** (not close > entryPrice)
- Minimum profit is based on **EMA distance** from entry (not close distance)
- Crossback checks **close < ema** for longs

### Python Bot (main.py) - **BUG FOUND AND FIXED:**
- WAS using `current_close > entry_price` for profitable check
- NOW uses `ema > entry_price` (matches Pine Script)

---

## SL Operator Difference

This might be causing issues:
- Pine: `low < slPrice` (STRICT)
- Python: `low <= slPrice` (INCLUSIVE)

When price exactly equals SL:
- Pine: NO stop
- Python: STOP

**RECOMMENDATION:** Change Python to use strict operators (`<` and `>`) to match Pine Script exactly.
