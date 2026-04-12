@echo off
title Saxo API Fetch
echo Starting data fetch from Saxo Bank...
python saxo_portfolio_fetcher.py %*
echo.
pause
