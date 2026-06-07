import yfinance as yf

ticker = yf.Ticker("BZ=F")

hist = ticker.history(period="5d")

print(hist)