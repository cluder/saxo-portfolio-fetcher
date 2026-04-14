# Saxo Portfolio Fetcher

A Python utility that securely fetches your portfolio, account balances, and open orders from the Saxo Bank API. It outputs a minimalistic JSON file that is optimized to be used as context for LLMs (like ChatGPT, Gemini, or Claude) for portfolio analysis.

## Features
- **Authentication**: Uses OAuth 2.0. Opens your browser to log in locally.
- **Minimal Output**: Automatically maps multi-currency accounts and removes irrelevant bank info, keeping only what matters (`Accounts`, `Portfolio`, `Orders`).
- **Archiving**: Old data files are moved to an `archive` folder.

## Prerequisites
- Python 3.x
- Saxo Developer app (for `AppKey` and `AppSecret`)

## Setup
1. Clone the repository and install dependencies (`pip install requests`).
2. Create a `saxo.info` file in the folder. Use the **COPY APP OBJECT** button on the [Saxo Developer Console](https://www.developer.saxo/openapi/appmanagement#/livedetails) and paste it. 
   *(Note: This file is ignored by `.gitignore` so your keys stay safe)*
   ```json
   {
       "AppKey": "YOUR_CLIENT_ID",
       "AppSecret": "YOUR_CLIENT_SECRET",
       "AuthorizationEndpoint": "https://live.logonvalidation.net/authorize",
       "TokenEndpoint": "https://live.logonvalidation.net/token",
       "OpenApiBaseUrl": "https://gateway.saxobank.com/openapi",
       "RedirectUrls": ["http://localhost"]
   }
   ```

## Usage
- **Windows (Recommended):** Double-click `Start_Saxo.bat`.
- **Terminal:** Run `python saxo_portfolio_fetcher.py`.
- **Debug Mode:** Run `python saxo_portfolio_fetcher.py --debug` (or `.\Start_Saxo.bat --debug`) to also save the original, uncleaned JSON payload provided by Saxo.

## Example Output
The tool will create a clean JSON file (e.g. `saxo_portfolio_20260414_084456.json`) that looks similar to this structure:
```json
{
  "Accounts": [
    {
      "Currency": "CHF",
      "CashBalance": 9999.99,
      "AccountValue": 99999.99,
      "MarginAvailable": 99999.99
    },
    {
      "Currency": "USD",
      "CashBalance": 999.99,
      "AccountValue": 9999.99,
      "MarginAvailable": 9999.99
    }
  ],
  "Portfolio": [
    {
      "Symbol": "AAPL:xnas",
      "Quantity": 99,
      "CurrentPrice": 999.99,
      "TotalValue": 99999.99,
      "ProfitLoss": 999.99,
      "ProfitLossPct": 9.99
    }
  ],
  "Orders": [
    {
      "OrderId": "99999999",
      "Symbol": "MSFT:xnas",
      "BuySell": "Buy",
      "Amount": 99,
      "Price": 999.99,
      "Status": "Working"
    }
  ]
}
```
