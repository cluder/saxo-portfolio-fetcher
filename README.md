# Saxo Portfolio Fetcher

This is a Python application that fetches your portfolio, account balances, and open orders from the Saxo Bank API via an OAuth 2.0 Authorization Code flow. It cleans up the raw response and outputs a minified JSON payload intended for further processing, for example for AI-driven portfolio analysis.

## Features
- **OAuth 2.0 Flow**: Automatically opens your browser and handles the authentication process securely locally.
- **Auto Refresh**: Token is saved and refreshed automatically for subsequent fetches.
- **Multicurrency**: Extracts data separating different sub-accounts (CHF, USD, etc.
- **LLM Optimized**: Strips all unnecessary markup from the Saxo OpenAPI and delivers a concise JSON outline containing `Accounts`, `Portfolio` positions, and `Orders`.
- **Archiving**: All existing local data files are moved into the `archive` directory upon successfully fetching new data.
- **Debug Mode**: The `--debug` flag allows keeping raw bank data JSON for deeper inspection of the original json, if required.

## Prerequisites
- Python 3.x
- `requests` library (`pip install requests`)
- A Saxo Bank developer application containing your `AppKey` and `AppSecret` (Saxo OpenAPI credentials).

## Setup
1. Clone this repository.
2. Provide your Saxo Bank OpenAPI parameters in a local `saxo.info` file. This is done by using the **COPY APP OBJECT** Button in the Saxo developer console for your app (https://www.developer.saxo/openapi/appmanagement#/livedetails) and paste it into the `saxo.info` file. **This file must be kept secret and is already ignored by `.gitignore`.** It must contain valid JSON format:
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
3. Run the script! 

## Usage
**Option 1: Windows Batch File (Recommended)**
Simply double-click the `Start_Saxo.bat` file. This starts the script in the foreground and leaves the window open until you press a key.

**Option 2: Terminal**
```bash
python saxo_portfolio_fetcher.py
```

**Debug Mode:**
To keep a copy of the raw Saxo API payload (before the LLM context optimization), run it with the `--debug` flag:
```bash
python saxo_portfolio_fetcher.py --debug
```
Or use the batch script like so: `.\Start_Saxo.bat --debug`
