# ---------- imports ---------- #
import os
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from datetime import datetime

# google sheets 
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
load_dotenv()

# ---------- connect to sql server ---------- #
sql_server_host = os.getenv("sql_server_host")
sql_server_user = os.getenv("sql_server_user")
sql_server_password = os.getenv("sql_server_password")
sql_server_database = os.getenv("sql_server_database")

connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={sql_server_host};DATABASE={sql_server_database};UID={sql_server_user};PWD={sql_server_password}'

conn = pyodbc.connect(connection_string)

# ---------- load data from the server ---------- #

# orders
orders_query = f"SELECT * FROM Orders"
ordersdf = pd.read_sql(orders_query, conn)

ordersdf

# invalid_rows = ordersdf[~ordersdf['price_total'].apply(pd.to_numeric, errors='coerce').notnull()]
# invalid_rows 
# ---------- Transformation ---------- #
ordersdf['createdAt'] = pd.to_datetime(ordersdf['createdAt'])
ordersdf = ordersdf[ordersdf['price_total'].apply(pd.to_numeric, errors='coerce').notnull()]
ordersdf['price_total'] = ordersdf['price_total'].astype(float)

rfm_df = ordersdf.groupby('_user').agg(
    recency=('createdAt', 'max'),
    frequency=('createdAt', 'count'),
    monetary_sum=('price_total', 'sum'),
    monetary_avg=('price_total', 'mean')
).reset_index()

rfm_df['monetary_sum'] = rfm_df['monetary_sum'].round(2)
rfm_df['monetary_avg'] = rfm_df['monetary_avg'].round(2)

today = datetime.today()
rfm_df['days_since_last_order'] = (today - rfm_df['recency']).dt.days

# rfm_df = rfm_df.sort_values(by='frequency', ascending=False)

# rfm_df


# ---------- upload dataframe to google sheets ---------- #
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
service_account = os.getenv("SERVICE_ACCOUNT")
sheet_name = "RFM_SHEET"  

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_file(service_account, scopes=scopes)

gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(google_sheet_id)

try:
    worksheet = spreadsheet.worksheet(sheet_name)
except gspread.exceptions.WorksheetNotFound:
    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")

worksheet.clear()  # Clears the content of the worksheet before overwriting
set_with_dataframe(worksheet, rfm_df)