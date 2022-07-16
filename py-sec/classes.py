import json
import os
import re
from ratelimit import limits
import pandas as pd
import requests
import datetime as dt
from tqdm.auto import tqdm
from user_agent import generate_user_agent


class DataJSON:
    def __init__(self, ticker):
        self.filepath = ''.join([os.getcwd(), '/data/company_tickers.json'])
        self.ticker = ticker


    def load_json(self):
        """for loading data from the default filepath, but, if necessary,
        also loads other json files"""

        try:
            data = pd.read_json(self.filepath)

        except ValueError:
            with open(self.filepath) as f:
                data = json.load(f)

        return data


    def save_json(self, df):
        """for saving loaded data back to default filepath
        does not support storing any objects other than pd.DataFrame"""

        try:
            df.to_json(path_or_buf=self.filepath)

        except ValueError:
            pass


    def get_cik_json(self):
        """loads company's CIK from default filepath"""

        with open(self.filepath) as f:
            data = json.load(f)

        for info in data.values():
            if info['ticker'] == self.ticker.upper():
                cik = info['cik_str']

                return cik


    def get_exchange_json(self):
        """loads company's exchange from default filepath"""

        with open(self.filepath) as f:
            f = json.load(f)

            for key, value in f.items():
                if value['ticker'] == self.ticker.upper():
                    exchange = value['exchange']

                    return exchange


class DataSEC(DataJSON):

    def __init__(self, ticker):
        super().__init__(ticker)
        self.cik = self.get_cik_json()
        self.random_ua = generate_user_agent()
        self.heads = {'Host': 'www.sec.gov', 'Connection': 'close',
                      'Accept': 'application/json, text/javascript, */*; q=0.01',
                      'X-Requested-With': 'XMLHttpRequest',
                      'User-Agent': self.random_ua,
                      }


    @limits(calls=10, period=1)
    def download_master_index(self, year=dt.date.today().year):

        qtr = 1
        while qtr < 5:
            try:
                url = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/master.idx"
                response = requests.get(url, headers=self.heads)
                response.raise_for_status()

                down_direct = os.getcwd() + '/data/edgar_master_index'

                filename = f'/master{year}QTR{qtr}.txt'
                path = ''.join([down_direct, filename])

                if not os.path.exists(path):
                    print(url)
                    with open(path, 'wb') as f:
                        f.write(response.content)

                qtr += 1

            except requests.HTTPError:
                continue


    @limits(calls=10, period=1)
    def get_filings(self, form='10-K'):
        """scrapes master index files for enpoints
        these endpoints are used to download excel files of company financials
        provided by the SEC"""

        master_index = ''.join([os.getcwd(), '/data/edgar_master_index/'])

        directory = os.listdir(master_index)

        r = re.compile(f'({form}).(\d+.\d+.\d+).(edgar/data/{self.cik}/)(' \
                       f'\d+.\d+.\d+)')

        downloads = []

        i = 0
        pbar = tqdm(total=len(directory))
        while i < len(directory):

            for file in directory:
                doc = master_index + file

                with open(doc, encoding='utf-8') as f:
                    try:
                        regex = r.findall(f.read())

                        for item in regex:
                            downloads.append(item)

                    except UnicodeDecodeError:
                        continue

            pbar.update(1)
            i += 1

        return downloads


    @limits(calls=10, period=1)
    def download_files(self, form='10-K'):
        """for downloading excel of company financials from SEC website"""
        downloads = self.get_filings()

        accession = [download[-1] for download in downloads]
        domain = [download[-2] for download in downloads]

        formatted_accession = [accession.pop().replace('-', '') for _ in
                               accession]

        formatted = [''.join([domain[0], number]) for number in
                     formatted_accession]

        dstdir = ''.join([os.getcwd(), f'/data/{self.ticker}_reports/'
                                       f'{form}s/xlsx/'])

        if not os.path.exists(dstdir):
            os.makedirs(dstdir)

        i = 0
        pbar = tqdm(total=len(formatted))
        while i < len(formatted):
            rename = f'{self.ticker}_report_{i}.xlsx'
            path = ''.join([dstdir, rename])

            try:
                url = f'https://www.sec.gov/Archives/' \
                      f'{formatted[i]}/Financial_Report.xlsx'

                req = requests.get(url, headers=self.heads, stream=True)

                if req.status_code == 200:
                    with open(path, 'wb') as f:
                        for chunk in req.iter_content(chunk_size=15000):
                            f.write(chunk)
                else:
                    continue

            except Exception:
                continue

            pbar.update(1)
            i += 1
        pbar.close()


    def excel_exception_helper(self):

        path = ''.join([os.getcwd(), f'/data/{self.ticker.lower()}_reports/'])
        directory = os.listdir(path)

        excel = []

        for workbook in directory:
            try:
                excel.append(pd.ExcelFile(path + workbook))

            except Exception:
                continue

        return excel


    def statement_regex(self, statement='income'):

        excel = self.excel_exception_helper()

        if statement.lower() == 'income':
            r = re.compile('^.*.Inc*.$')

        elif statement.lower() == 'balance':
            r = re.compile('^.*.Balance.Sheets*.$')

        elif statement.lower() == 'cash flow':
            r = re.compile('^.*.Cash*.$')

        for i in excel:
            sheet_name = list(filter(r.match, i.sheet_names)).pop()

            return sheet_name


    def load_income_statements_xlsx(self, form='10-K'):

        """imports downloaded excel files as pandas dataframes and appends them
        to list"""

        sheets = []

        path = ''.join(
            [os.getcwd(), f'/data/{self.ticker}_reports/{form}s/xlsx/'])

        if not os.path.exists(path):
            self.download_files(form=form)

        directory = os.listdir(path)

        for file in tqdm(directory):
            try:
                filename = ''.join([path, file])

                sheet_name = 'Consolidated_Statements_of_Inc'
                df = pd.read_excel(filename, sheet_name=sheet_name)
                sheets.append(df)

            except ValueError:
                try:
                    filename = path + file
                    sheet_name = 'Consolidated Statements of Inco'
                    df = pd.read_excel(filename, sheet_name=sheet_name)
                    sheets.append(df)
                except ValueError:
                    continue

        return sheets


    def load_balance_sheets_xlsx(self, form='10-K'):

        """imports downloaded excel files as pandas dataframes and appends them
        to list"""

        sheets = []

        path = ''.join(
            [os.getcwd(), f'/data/{self.ticker}_reports/{form}s/xlsx/'])

        if not os.path.exists(path):
            self.download_files(form=form)

        directory = os.listdir(path)

        for file in tqdm(directory):
            try:
                filename = path + file

                sheet_name = 'Consolidated_Balance_Sheets'
                df = pd.read_excel(filename, sheet_name=sheet_name)
                sheets.append(df)

            except ValueError:
                try:
                    filename = path + file
                    sheet_name = 'Consolidated Balance Sheets'
                    df = pd.read_excel(filename, sheet_name=sheet_name)
                    sheets.append(df)
                except ValueError:
                    continue

        return sheets


    def load_cash_flow_statements_xlsx(self, form='10-K'):

        """imports downloaded excel files as pandas dataframes and appends them
        to list"""

        sheets = []

        path = ''.join(
            [os.getcwd(), f'/data/{self.ticker}_reports/{form}s/xlsx/'])

        if not os.path.exists(path):
            self.download_files(form=form)

        directory = os.listdir(path)

        for file in tqdm(directory):
            try:
                filename = path + file

                sheet_name = 'Consolidated_Statements_of_Cash'
                df = pd.read_excel(filename, sheet_name=sheet_name)
                sheets.append(df)

            except ValueError:
                try:
                    filename = path + file
                    sheet_name = 'Consolidated Statements of Cash'
                    df = pd.read_excel(filename, sheet_name=sheet_name)
                    sheets.append(df)
                except ValueError:
                    continue

        return sheets


    def to_csv(self, statement='all', form='10-K'):

        if statement == 'income':
            statements = self.load_income_statements_xlsx()
            folder = 'income_statements'

        elif statement == 'balance':
            statements = self.load_balance_sheets_xlsx()
            folder = 'balance_sheets'

        elif statement == 'cash':
            statements = self.load_cash_flow_statements_xlsx()
            folder = 'cash_flow_statements'

        elif statement == 'all':
            statements = [self.load_income_statements_xlsx(),
                          self.load_balance_sheets_xlsx(),
                          self.load_cash_flow_statements_xlsx()]
            folders = ['income_statements', 'balance_sheets',
                       'cash_flow_statements']

        try:
            path = ''.join([os.getcwd(), f'/data/{self.ticker}_reports/'
                                         f'{form}s/csv/{folder}/'])

            if not os.path.exists(path):
                os.makedirs(path)

            i = 0
            while i < len(statements):
                file = ''.join([path, f'statements_{i}.csv'])
                statements[i].to_csv(path_or_buf=file)
                i += 1

        except Exception:

            i = 0
            while i < len(statements):
                path = ''.join([os.getcwd(), f'/data/{self.ticker}_reports/'
                                             f'{form}s/csv/{folders[i]}/'])

                if not os.path.exists(path):
                    os.makedirs(path)

                j = 0
                while j < len(statements[i]):
                    file = ''.join([path, f'statements_{j}.csv'])
                    statements[i][j].to_csv(path_or_buf=file)
                    j += 1
                i += 1


    def load_income_statements_csv(self, form='10-K'):

        sheets = []

        path = ''.join([os.getcwd(), f'/data/{self.ticker}_reports/'
                                     f'{form}s/csv/income_statements/'])

        if not os.path.exists(path):
            self.to_csv(statement='income')

        directory = os.listdir(path)

        for file in tqdm(directory):
            try:
                filename = ''.join([path, file])
                df = pd.read_csv(filename)
                sheets.append(df)

            except Exception:
                continue

        return sheets


    def load_balance_sheets_csv(self, form='10-K'):

        sheets = []

        path = ''.join([os.getcwd(), f'/data/{self.ticker}_reports/'
                                     f'{form}s/csv/balance_sheets/'])

        if not os.path.exists(path):
            self.to_csv(statement='balance')

        directory = os.listdir(path)

        for file in tqdm(directory):
            try:
                filename = ''.join([path, file])
                df = pd.read_csv(filename)
                sheets.append(df)

            except Exception:
                continue

        return sheets


    def load_cash_flow_statements_csv(self, form='10-K'):

        sheets = []

        path = ''.join([os.getcwd(), f'/data/{self.ticker}_reports/'
                                     f'{form}s/csv/cash_flow_statements/'])

        if not os.path.exists(path):
            self.to_csv(statement='cash')

        directory = os.listdir(path)

        for file in tqdm(directory):
            try:
                filename = ''.join([path, file])
                df = pd.read_csv(filename)
                sheets.append(df)

            except Exception:
                continue

        return sheets