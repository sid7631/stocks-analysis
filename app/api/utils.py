import pandas as pd
import datetime
import json
from pathlib import Path

def tax_stocks(file_path,start_date=None,end_date=None):
    icici_tax_statement_mapping = {
        'column_names':{'Description':'category','Stock Symbol':'symbol','Quantity':'quantity','Sale Date':'sale_date','Sale Rate':'sale_rate','Sale Value':'sale_value','Purchase Date':'purchase_date','Purchase Rate':'purchase_rate','Purchase Value':'purchase_value','Profit/Loss(-)':'pnl'}
    }
    sheet_mapping = icici_tax_statement_mapping
    df = pd.read_csv(file_path, skiprows=2)
    #interpolate first column with nearest value
    df.iloc[:,0] = df.iloc[:,0].ffill()
    #drop any column with nan
    df.drop(df.index[df.isnull().any(1)], inplace=True)
    #reset index
    df.reset_index(drop=True,inplace=True)
    #make first row column and remove the first row
    # df.columns = df.iloc[0]
    # df = df[1:]
    #rename columns based on mapping
    df.columns = df.columns.to_series().map(sheet_mapping['column_names'])

    df['sale_date'] = pd.to_datetime(df['sale_date']).dt.date
    df['purchase_date'] = pd.to_datetime(df['purchase_date']).dt.date
    df['label'] = df['pnl'].apply(lambda x: 'loss' if x.startswith('-') else 'profit')
    for column in ['sale_rate','sale_value','purchase_rate','purchase_value','pnl']:
        df[column] = df[column].apply(lambda x: x.replace('-','').replace(',',''))
        df[column] = pd.to_numeric(df[column])
    if start_date and end_date:
        x = datetime.datetime.strptime(start_date,'%d-%m-%Y').date()
        y = datetime.datetime.strptime(end_date,'%d-%m-%Y').date()
        df_date_filtered = df[(df['sale_date']>=x) & (df['sale_date']<=y)]
    else:
        df_date_filtered = df
        start_date = df['sale_date'].min()
        end_date = df['sale_date'].max()
    df_result = pd.DataFrame(df_date_filtered.groupby(['category','label'])['pnl'].sum().reset_index())
    return {'records':json.loads(df_result.to_json(orient='records')), 'from':start_date, 'to':end_date}


def create_folder(path):
    Path(path).mkdir(parents=True, exist_ok=True)