from urllib.parse import urlencode
import requests
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import threading
import os
import datetime

import sys
import glob
import shutil

# --- CONFIGURATION ---
SAXO_INFO_FILE = "saxo.info"
TOKEN_FILE = "saxo_token.json"

try:
    with open(SAXO_INFO_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Error: The configuration file '{SAXO_INFO_FILE}' was not found.")
    print("Please download the app information from Saxo, save it to this file and add it to .gitignore.")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"Error: The file '{SAXO_INFO_FILE}' does not contain valid JSON.")
    sys.exit(1)

CLIENT_ID = config.get("AppKey")
CLIENT_SECRET = config.get("AppSecret")
_redirect_urls = config.get("RedirectUrls", ["http://localhost"])
REDIRECT_URI = _redirect_urls[0] if _redirect_urls else "http://localhost"

AUTH_ENDPOINT = config.get("AuthorizationEndpoint", "https://live.logonvalidation.net/authorize")
TOKEN_ENDPOINT = config.get("TokenEndpoint", "https://live.logonvalidation.net/token")
BASE_URL = config.get("OpenApiBaseUrl", "https://gateway.saxobank.com/openapi").rstrip('/')

if not CLIENT_ID or not CLIENT_SECRET:
    print(f"Error: The file '{SAXO_INFO_FILE}' must contain at least 'AppKey' and 'AppSecret'.")
    sys.exit(1)

auth_code = None

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urlparse(self.path).query
        params = parse_qs(query)
        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication successful!</h1><p>You can now close this window and return to the terminal.</p></body></html>")
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication failed!</h1><p>No code found.</p></body></html>")
            
        # Stop server (in its own thread, since we are still in the request)
        threading.Thread(target=self.server.shutdown).start()

    def log_message(self, format, *args):
        return # Suppress server logs

def get_new_token():
    global auth_code
    auth_code = None
    
    query_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'state': 'randomstate123',
        'redirect_uri': REDIRECT_URI
    }
    
    auth_url = f"{AUTH_ENDPOINT}?{urlencode(query_params)}"
    
    print("Opening browser for authentication (Authorization Code Flow)...")
    webbrowser.open(auth_url)
    
    server_address = ('', 80)
    httpd = HTTPServer(server_address, AuthHandler)
    print("Waiting for successful login in the browser (Port 80)...")
    httpd.serve_forever()
    httpd.server_close()
    
    if not auth_code:
        print("Error: Could not obtain Authorization Code.")
        return None
        
    print("Authorization Code obtained. Fetching token...")
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI
    }
    
    response = requests.post(TOKEN_ENDPOINT, data=data)
    if response.status_code in [200, 201]:
        token_info = response.json()
        print("Token generated successfully.")
        # Save the token for future use (and refresh token)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_info, f)
        return token_info.get('access_token')
    else:
        print(f"Error fetching token: {response.status_code}")
        print(response.text)
        return None

def refresh_access_token(refresh_token):
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(TOKEN_ENDPOINT, data=data)
    if response.status_code in [200, 201]:
        token_info = response.json()
        # If no new refresh_token is returned, keep the old one
        if 'refresh_token' not in token_info:
            token_info['refresh_token'] = refresh_token
            
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_info, f)
        return token_info.get('access_token')
    else:
        print(f"Error refreshing token: {response.status_code}")
        print(response.text)
        return None

def get_access_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                token_info = json.load(f)
            
            refresh_token = token_info.get('refresh_token')
            if refresh_token:
                print("Attempting to renew token (Refresh)...")
                new_token = refresh_access_token(refresh_token)
                if new_token:
                    print("Token successfully renewed.")
                    return new_token
        except Exception as e:
            print(f"Could not use saved token ({e}). Fetching new one...")
            
    # Fallback: Fetch a new token
    return get_new_token()

def extract_data(raw_data):
    data = {
        "_Documentation": "Note: For cash-based trading decisions, strictly utilize 'CashAvailableForTrading'. 'ProjectedCashAfterOrdersExecuted' reflects your remaining cash assuming all current open buy orders are filled. 'MarginAvailableForTrading' includes the collateral value of held securities; utilizing it involves borrowing broker funds and will incur overnight interest charges.",
        "Accounts": {},
        "Portfolio": [],
        "Orders": []
    }
    
    if "accounts" in raw_data and "balances_by_account" in raw_data:
        for acc in raw_data["accounts"].get("Data", []):
            acc_key = acc.get("AccountKey")
            acc_id = acc.get("AccountId")
            currency = acc.get("Currency")
            
            bal = raw_data["balances_by_account"].get(acc_key, {})
            if bal:
                data["Accounts"][acc_id] = {
                    "DisplayName": acc.get("DisplayName"),
                    "AccountType": acc.get("AccountType"),
                    "ManagementType": acc.get("ManagementType"),
                    "Currency": currency,
                    "TotalValue": bal.get("TotalValue"),
                    "CashBalance": bal.get("CashBalance"),
                    "CashAvailableForTrading": bal.get("CashAvailableForTrading"),
                    "MarginAvailableForTrading": bal.get("MarginAvailableForTrading"),
                    "UnrealizedProfitLoss": bal.get("UnrealizedPositionsValueExcludingCostToClosePositions") or bal.get("UnrealizedPositionsValue") or 0.0,
                    "OpenOrdersValue": 0.0,
                    "ProjectedCashAfterOrdersExecuted": 0.0
                }
        
    if "portfolio" in raw_data and "Data" in raw_data["portfolio"]:
        for pos in raw_data["portfolio"]["Data"]:
            fmt = pos.get("DisplayAndFormat", {})
            base = pos.get("PositionBase", {})
            view = pos.get("PositionView", {})
            
            data["Portfolio"].append({
                "AccountId": base.get("AccountId"),
                "Name": fmt.get("Description"),
                "Symbol": fmt.get("Symbol"),
                "AssetType": base.get("AssetType"),
                "Amount": base.get("Amount"),
                "PurchasePrice": base.get("OpenPrice"),
                "CurrentPrice": view.get("CurrentPrice"),
                "MarketValue": view.get("MarketValue"),
                "ProfitLoss": view.get("ProfitLossOnTrade"),
                "Currency": fmt.get("Currency")
            })
            
    if "orders" in raw_data and "Data" in raw_data["orders"]:
        for ord in raw_data["orders"]["Data"]:
            fmt = ord.get("DisplayAndFormat", {})
            dur = ord.get("Duration", {})
            
            acc_id = ord.get("AccountId")
            action = ord.get("BuySell")
            amount = ord.get("Amount", 0)
            price = ord.get("Price", 0)
            
            data["Orders"].append({
                "AccountId": acc_id,
                "Name": fmt.get("Description"),
                "Symbol": fmt.get("Symbol"),
                "Type": ord.get("OpenOrderType"),
                "DurationType": dur.get("DurationType"),
                "ExpirationDate": dur.get("ExpirationDateTime") or dur.get("ExpirationDate"),
                "Action": action,
                "Amount": amount,
                "TargetPrice": price,
                "DistanceToMarket": ord.get("DistanceToMarket")
            })
            
            if action == "Buy" and acc_id in data["Accounts"]:
                data["Accounts"][acc_id]["OpenOrdersValue"] += (amount * price)
                
    for acc_id, acc_info in data["Accounts"].items():
        if acc_info["CashAvailableForTrading"] is not None:
            acc_info["ProjectedCashAfterOrdersExecuted"] = acc_info["CashAvailableForTrading"] - acc_info["OpenOrdersValue"]
            
    return data

def fetch_saxo_data():
    access_token = get_access_token()
    if not access_token:
        print("Abort: No valid Access Token available.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    data_collection = {}

    print("Downloading data...")

    # 0. Fetch accounts to process separate currencies (CHF/USD)
    res_accounts = requests.get(f"{BASE_URL}/port/v1/accounts/me", headers=headers)
    if res_accounts.status_code == 200:
        data_collection["accounts"] = res_accounts.json()
        print("- Accounts loaded successfully.")
        
        data_collection["balances_by_account"] = {}
        for acc in data_collection["accounts"].get("Data", []):
            acc_key = acc["AccountKey"]
            client_key = acc["ClientKey"]
            res_bal = requests.get(f"{BASE_URL}/port/v1/balances?AccountKey={acc_key}&ClientKey={client_key}", headers=headers)
            if res_bal.status_code == 200:
                data_collection["balances_by_account"][acc_key] = res_bal.json()
        print("- Individual account balances loaded successfully.")
    else:
        print(f"- Error fetching accounts: {res_accounts.status_code}")

    # 1. Fetch overall balance (Global Balance) (as backup/overview)
    res_balance = requests.get(f"{BASE_URL}/port/v1/balances/me", headers=headers)
    if res_balance.status_code == 200:
        data_collection["balance"] = res_balance.json()
    else:
        print(f"- Error fetching overall balance: {res_balance.status_code}")

    # 2. Fetch open positions (Portfolio) including all relevant price and name data
    res_positions = requests.get(f"{BASE_URL}/port/v1/positions/me?FieldGroups=DisplayAndFormat,PositionBase,PositionView", headers=headers)
    if res_positions.status_code == 200:
        data_collection["portfolio"] = res_positions.json()
        print("- Portfolio loaded successfully.")
    else:
        print(f"- Error fetching portfolio: {res_positions.status_code}")

    # 3. Fetch active orders including price and format data
    res_orders = requests.get(f"{BASE_URL}/port/v1/orders/me?FieldGroups=DisplayAndFormat", headers=headers)
    if res_orders.status_code == 200:
        data_collection["orders"] = res_orders.json()
        print("- Orders loaded successfully.")
    else:
        print(f"- Error fetching orders: {res_orders.status_code}")

    # Move existing files into archive before creating new ones
    archive_dir = "archive"
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        
    for f in glob.glob("*portfolio*.json"):
        shutil.move(f, os.path.join(archive_dir, f))
    if "--debug" in sys.argv:
        for f in glob.glob("*raw*.json"):
            shutil.move(f, os.path.join(archive_dir, f))
    else:
        for f in glob.glob("*raw*.json"):
            os.remove(f)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if "--debug" in sys.argv:
        # Save raw data to a file for easy reading
        filename_raw = f"my_saxo_data_raw_{timestamp}.json"
        with open(filename_raw, "w", encoding="utf-8") as f:
            json.dump(data_collection, f, indent=4)
        
    # Save extracted data
    data = extract_data(data_collection)
    filename = f"saxo_portfolio_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    if "--debug" in sys.argv:
        print(f"\nDone! The raw data is located in '{filename_raw}' and the cleaned up data in '{filename}'.")
    else:
        print(f"\nDone! The cleaned up data is located in '{filename}'.")

if __name__ == "__main__":
    fetch_saxo_data()