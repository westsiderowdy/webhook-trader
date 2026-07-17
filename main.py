import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

app = FastAPI()

# 1. Connect safely to Alpaca using Render Environment Variables
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
IS_PAPER = os.getenv("ALPACA_PAPER", "True").lower() == "true"

# Initialize the official modern Alpaca Client
trading_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=IS_PAPER)

# Data model for incoming trade signals
class TradeSignal(BaseModel):
    symbol: str        # e.g., "AAPL" or "BTCUSD"
    action: str        # "buy" or "sell"
    qty: float         # How many shares/coins to trade
    passphrase: str    # Simple password to keep your endpoint secure

@app.get("/")
@app.get("/health")
def health_check():
    """Keep-alive endpoint. External pingers hit this to prevent Render from sleeping."""
    return {"status": "healthy", "message": "Bot is awake and ready to route orders!"}

@app.post("/webhook")
async def receive_webhook(signal: TradeSignal):
    # Security passphrase protection
    if signal.passphrase != os.getenv("WEBHOOK_PASSPHRASE", "mysecret123"):
        raise HTTPException(status_code=401, detail="Unauthorized signal attempt")

    try:
        # Determine trade direction
        side = OrderSide.BUY if signal.action.lower() == "buy" else OrderSide.SELL
        
        # Format the market order parameters properly
        market_order_data = MarketOrderRequest(
            symbol=signal.symbol.upper(),
            qty=signal.qty,
            side=side,
            time_in_force=TimeInForce.GTC
        )
        
        # Fire the order straight to your Alpaca paper account
        order = trading_client.submit_order(order_data=market_order_data)
        
        return {"status": "success", "order_id": str(order.id), "message": f"Executed {signal.action} for {signal.qty} shares of {signal.symbol}"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
