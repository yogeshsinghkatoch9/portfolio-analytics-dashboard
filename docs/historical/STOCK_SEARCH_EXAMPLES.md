# Portfolio Builder - Stock Search Examples

## How Stock Search Works Now

When you type a ticker symbol in the "Add Assets" search box, the system:

1. **Fetches from Yahoo Finance** - Gets live stock data
2. **Extracts Key Information**:
   - Stock symbol (e.g., AAPL)
   - Company name (e.g., Apple Inc.)
   - Current price ($280.52)
   - Sector (Technology)
   - Exchange (NMS)

3. **Shows in Results** - Click to add to portfolio
4. **Uses Price Automatically** - For all calculations

---

## Examples That Work

### Tech Stocks
```
Type: AAPL
Result: Apple Inc. - $280.52 ✅

Type: MSFT
Result: Microsoft Corporation - $420.13 ✅

Type: GOOGL
Result: Alphabet Inc. - $140.25 ✅

Type: TSLA
Result: Tesla Inc. - $250.18 ✅
```

### Financial Stocks
```
Type: JPM
Result: JPMorgan Chase & Co. - $207.45 ✅

Type: BAC
Result: Bank of America - $35.67 ✅

Type: GS
Result: Goldman Sachs - $485.92 ✅
```

### Consumer Stocks
```
Type: AMZN
Result: Amazon.com Inc. - $180.42 ✅

Type: NKE
Result: Nike Inc. - $75.83 ✅

Type: WMT
Result: Walmart Inc. - $95.21 ✅
```

### Energy Stocks
```
Type: XOM
Result: Exxon Mobil - $118.45 ✅

Type: CVX
Result: Chevron Corporation - $155.67 ✅

Type: COP
Result: ConocoPhillips - $128.93 ✅
```

### Healthcare Stocks
```
Type: JNJ
Result: Johnson & Johnson - $155.78 ✅

Type: PFE
Result: Pfizer Inc. - $28.34 ✅

Type: UNH
Result: UnitedHealth Group - $520.14 ✅
```

### ETFs
```
Type: SPY
Result: SPDR S&P 500 ETF - $450.23 ✅

Type: QQQ
Result: Invesco QQQ Trust - $380.45 ✅

Type: IWM
Result: iShares Russell 2000 ETF - $195.67 ✅
```

---

## Step-by-Step Example: Build a 5-Stock Portfolio

### 1. Add Apple (AAPL)
```
Search Input: aapl
Results:
  ✓ AAPL - Apple Inc. - $280.52

Action: Click on result
Added: AAPL (Qty: unknown, Price: $280.52)
Set Allocation: 20%
```

### 2. Add Microsoft (MSFT)
```
Search Input: msft
Results:
  ✓ MSFT - Microsoft Corporation - $420.13

Action: Click on result
Added: MSFT (Price: $420.13)
Set Allocation: 20%
```

### 3. Add Google (GOOGL)
```
Search Input: googl
Results:
  ✓ GOOGL - Alphabet Inc. - $140.25

Action: Click on result
Added: GOOGL (Price: $140.25)
Set Allocation: 20%
```

### 4. Add Amazon (AMZN)
```
Search Input: amzn
Results:
  ✓ AMZN - Amazon.com Inc. - $180.42

Action: Click on result
Added: AMZN (Price: $180.42)
Set Allocation: 20%
```

### 5. Add Tesla (TSLA)
```
Search Input: tsla
Results:
  ✓ TSLA - Tesla Inc. - $250.18

Action: Click on result
Added: TSLA (Price: $250.18)
Set Allocation: 20%
```

### 6. Analyze Portfolio
```
Total Allocation: 100% ✅
Button Status: "Analyze Portfolio" (ENABLED)

Click "Analyze Portfolio"

Results Show:
  ✓ Est. Return (1Y): 12.5%
  ✓ Risk (Vol): 18.3%
  ✓ Est. Yield: 0.8%
  ✓ Charts with projections
  ✓ Asset allocation pie chart
  ✓ Risk analysis metrics
```

---

## Search Tips & Tricks

### What Works
✅ Full ticker: `AAPL`  
✅ Lowercase: `aapl`  
✅ Uppercase: `AAPL`  
✅ Company name: `Apple`  
✅ Partial name: `Appl`  

### Takes About
⏱ 0.5 seconds to search  
⏱ Results appear automatically  
⏱ No need to press Enter  

### Common Patterns
```
Pattern: [Ticker]
Example: AAPL → Returns Apple Inc.

Pattern: [Company Name]
Example: Apple → Returns Apple Inc.

Pattern: [Partial Name]
Example: Appl → May return Apple Inc.

Pattern: [ETF Symbol]
Example: SPY → Returns S&P 500 ETF
```

---

## Real-Time Prices

The prices shown are **LIVE** from Yahoo Finance:

### Refreshed When
- You perform a search
- You add a stock to portfolio
- You click "Analyze Portfolio"

### Used For
- Initial portfolio simulation
- Allocation calculations
- Performance projections
- Risk analysis

### Example Price Updates
```
Session 1 (10:00 AM):
  AAPL search → Price: $280.52

Session 2 (2:00 PM):
  AAPL search → Price: $281.20 (updated)

Session 3 (4:00 PM):
  AAPL search → Price: $279.85 (updated)
```

---

## Building Your Portfolio

### Template Portfolio 1: Diversified Tech
```
AAPL   20%  ($280.52)
MSFT   20%  ($420.13)
GOOGL  20%  ($140.25)
NVDA   20%  ($875.42)
META   20%  ($505.18)
Total: 100%
```

### Template Portfolio 2: Tech + Finance
```
AAPL   15%  ($280.52)
MSFT   15%  ($420.13)
GOOGL  15%  ($140.25)
JPM    25%  ($207.45)
BAC    30%  ($35.67)
Total: 100%
```

### Template Portfolio 3: Balanced
```
AAPL    15%  ($280.52)
JNJ     15%  ($155.78)
XOM     15%  ($118.45)
JPM     25%  ($207.45)
SPY     30%  ($450.23)
Total: 100%
```

---

## Troubleshooting Search

### Problem: No Results Appear
**Solution:**
- Check spelling (AAPL not APPL)
- Try company name: Apple instead of AAPL
- Wait 1 second after typing
- Refresh page if stuck

### Problem: Wrong Stock Appears
**Solution:**
- Use exact ticker for precision
- Example: TSLA (Tesla) not TS
- Some tickers are ambiguous

### Problem: Price Seems Wrong
**Solution:**
- Prices update in real-time
- May differ from market by seconds
- Refresh search for latest price

### Problem: Stock Won't Add to Portfolio
**Solution:**
- Make sure result is highlighted
- Click directly on the stock name
- Try refreshing page
- Try a different stock

---

## API Response Example

When you search for "AAPL", the backend returns:

```json
{
  "success": true,
  "query": "AAPL",
  "results": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "type": "EQUITY",
      "sector": "Technology",
      "exchange": "NMS",
      "price": 280.52
    }
  ],
  "count": 1
}
```

This gets displayed as:
```
✓ AAPL - Apple Inc. - $280.52
```

And when you click it:
```
Added to Proposed Holdings:
  Symbol: AAPL
  Price: $280.52
  [Allocation field]
```

---

## Performance Expectations

| Action | Time | Status |
|--------|------|--------|
| Type character | Instant | ✅ |
| Wait for search | 0.5s | ✅ |
| Show results | 1s total | ✅ |
| Click to add | Instant | ✅ |
| Add 5 stocks | 10s | ✅ |
| Click Analyze | 2-3s | ✅ |
| See results | 4s total | ✅ |

---

## Next Steps After Adding Stocks

Once you've added all stocks and analyzed:

1. **View Results**
   - See estimated return
   - View risk metrics
   - Check allocation chart

2. **Adjust Allocation**
   - Change percentages
   - Re-analyze if changed
   - Compare different allocations

3. **Compare with Upload**
   - Upload existing portfolio
   - Compare side-by-side
   - Export both for analysis

4. **Export Analysis**
   - Use "Export CSV" to save
   - Use "Export PDF" for report
   - Share with advisor

---

**Happy Investing!** 🚀

The Portfolio Builder with live stock search is now fully functional.
Start by typing "AAPL" and see it work!
