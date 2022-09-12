import argparse
import openpyxl

def option():
    parser = argparse.ArgumentParser(
        description=''
    )
    parser.add_argument('-v', '--version',
                        help='version information',
                        action='version',
                        version='%(prog)s 0.1'
                        )
    parser.add_argument('-o', '--output',
                        help='specifiy output folder',
                        action='store',
                        default='out'
                        )
    parser.add_argument('-k', '--keyword-file',
                        help='input keyword file',
                        default='keyword.xlsx')
    parser.add_argument('-a', '--appid_file',
                        help='appid',
                        default='appid.xlsx'
                        )
    parser.add_argument('-n', '--number',
                        help='max number of search result',
                        default='max_number')
    return parser.parse_args()

def load_xlsx_cells(xlsx:str):
    wb = openpyxl.load_workbook(xlsx)
    ws = wb[wb.sheetnames[0]]

    values = []
    clm = 0
    for r in range(ws.max_row):
        cell = ws['A'+str(r+1)]
        values.append(cell.value)
    return values


def load_keywords(keyword_file:str):
    keywords = load_xlsx_cells(keyword_file)
    return keywords


def load_appids(appid_file: str):
    appids = load_xlsx_cells(appid_file)
    return appids


def main():
    args = option()
    print(args)
    keywords = load_keywords(args.keyword_file)
    appids = load_appids(args.appid_file)
    return 0


if __name__ == '__main__':
    exit(main())
