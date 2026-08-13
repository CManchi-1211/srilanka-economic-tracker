import datetime
import os
import json
import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials

# Google Authentication using GitHub Secret
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Read credentials from environment variable set in GitHub Actions
gcp_key = os.environ.get("GCP_SA_KEY")
service_account_info = json.loads(gcp_key)
creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(creds)

# Dynamic Year Handling & Fetching Data
start_year = 1990
current_year = datetime.datetime.now().year

cpi_rate_url = f"http://api.worldbank.org/v2/country/LKA/indicator/FP.CPI.TOTL.ZG?format=json&date={start_year}:{current_year}&per_page=100"
cpi_index_url = f"http://api.worldbank.org/v2/country/LKA/indicator/FP.CPI.TOTL?format=json&date={start_year}:{current_year}&per_page=100"
ex_url = f"http://api.worldbank.org/v2/country/LKA/indicator/PA.NUS.FCRF?format=json&date={start_year}:{current_year}&per_page=100"

res_cpi_rate = requests.get(cpi_rate_url).json()[1]
res_cpi_index = requests.get(cpi_index_url).json()[1]
res_ex = requests.get(ex_url).json()[1]

df_cpi_rate = pd.DataFrame([{"Year": str(x["date"]), "Inflation_Rate_%": x["value"]} for x in res_cpi_rate])
df_cpi_index = pd.DataFrame([{"Year": str(x["date"]), "CPI_Cost_of_Living_Index": x["value"]} for x in res_cpi_index])
df_ex = pd.DataFrame([{"Year": str(x["date"]), "USD_LKR_Exchange_Rate": x["value"]} for x in res_ex])

new_df = pd.merge(df_cpi_rate, df_cpi_index, on="Year")
new_df = pd.merge(new_df, df_ex, on="Year").sort_values("Year").reset_index(drop=True)
new_df = new_df.fillna("")

# Open Target Google Sheet
spreadsheet_name = "SriLanka_Live_Economic_Data"
sh = gc.open(spreadsheet_name)
worksheet = sh.sheet1

# Smart Update Process
existing_data = worksheet.get_all_records()

if existing_data:
    existing_df = pd.DataFrame(existing_data)
    existing_df["Year"] = existing_df["Year"].astype(str)
    combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["Year"], keep="last").sort_values("Year")
else:
    combined_df = new_df

# Overwrite Worksheet
worksheet.clear()
worksheet.update([combined_df.columns.values.tolist()] + combined_df.values.tolist())

print("✅ Success! Live data pipeline executed successfully via GitHub Actions.")
