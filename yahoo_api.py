import os
import time
import httpx
import openpyxl

import queue
import threading

itemSearch_ep = 'https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch'
max_rpm = 30 # max requests per minute
MAX_RETURNED_RESULTS = 1000
MAX_ITEMS_NUM = 10000


def create_query_params(appid, get_results, add_params={}):
    params = {'appid': appid,
                'results': get_results}
    for k, v in add_params.items():
        params[k] = v # 同一キーは上書き
    return params


def retry_request(client: httpx.Client):
    MAX_TMR_NUM = 5 # 429: Too Many Requests を連続で返却されたときの許容数
    tmr_cnt = 1
    while tmr_cnt < MAX_TMR_NUM:
        print('...retry cnt:', tmr_cnt)
        time.sleep(60) # 1分のチェックあたりまで待機
        print('retry...')
        r = client.get(url=itemSearch_ep)
        if r.status_code == 200:
            tmr_cnt = 0
            return r
        print('[-] Error', r.status_code, r.text)
        tmr_cnt += 1
    print('[-] Error', 'OVER MAX retry number')
    return None


def recieve_response(r:httpx.Response, client: httpx.Client):
    if r.status_code == 200:
        rData = r.json()
        print('[+]Check results:', rData['totalResultsAvailable'], rData['totalResultsReturned'], rData['firstResultsPosition'], client.params)
        return r.json()
    elif r.status_code == 429:
        # Too Many Requests
        print("[-]Error: Too Many Requests.", client.params)
        r = retry_request(client)
        if not r:
            print('[-] Too Many Request')
            return None
        return r.json()
    else:
        print('Status Code:', r.status_code, ', Text:', r.text, client.params)
        return None



def create_price_range(params: dict, price_start=1):
    price_range = []
    pStart = price_start
    local_params = {}
    for k, v in params.items():
        local_params[k] = v
    # 降順で最大金額を取得
    local_params['sort'] = '-price'
    client = httpx.Client(params=local_params)
    r = client.get(url=itemSearch_ep)
    rData = recieve_response(r, client)
    pStart, pEnd = price_start, rData['hits'][0]['price']
    totalResults = rData['totalResultsAvailable']
    tmp_list = [[totalResults, pStart, pEnd]]
    if totalResults < MAX_RETURNED_RESULTS:
        return tmp_list

    # 検索結果がMAX_RETURNED_RESULTSに収まる価格範囲のリストを作成
    local_params['sort'] = '+price'
    pFrom, pTo = pStart, pEnd
    while True:
        if not tmp_list:
            break
        _, pFrom, pTo = tmp_list[-1]
        local_params['price_from'] = pFrom
        middle = (pFrom + pTo) // 2
        local_params['price_to'] = middle
        client = httpx.Client(params=local_params)
        r = client.get(url=itemSearch_ep)
        rData = recieve_response(r, client)
        if not rData:
            break
        availableResults = rData['totalResultsAvailable']
        if availableResults == 0:
            tmp_list[-1][1] = middle + 1
        elif availableResults < MAX_RETURNED_RESULTS:
            price_range.append([availableResults, pFrom, middle])
            tmp_list[-1][0] -= availableResults
            tmp_list[-1][1] = middle + 1
            if tmp_list[-1][0] == 0:
                del tmp_list[-1]
            elif tmp_list[-1][0] < MAX_RETURNED_RESULTS:
                price_range.append(tmp_list.pop())
        else:
            new_elm = [availableResults, pFrom, middle]
            tmp_list[-1][0] -= new_elm[0]
            tmp_list[-1][1] = middle + 1
            if tmp_list[-1][0] == 0:
                del tmp_list[-1]
            elif tmp_list[-1][0] < MAX_RETURNED_RESULTS:
                price_range.append(tmp_list.pop())
            elif tmp_list[-1][1] == tmp_list[-1][2]:
                price_range.append(tmp_list.pop())

            if pFrom == middle:
                print('[+] cut results', middle, availableResults)
                price_range.append(new_elm)
            else:
                tmp_list.append(new_elm)
    price_range.sort(key=lambda x: x[1])
    print('[+]Get Price-Range:', price_range)
    S = 0
    for pr in price_range:
        S += pr[0]
    assert S == totalResults
    return price_range

class SearchItemOfShop(threading.Thread):
    def __init__(self, appid, shop_queue: queue.Queue):
        super(SearchItemOfShop, self).__init__()
        self.appid = appid
        self.get_results = 100
        self.shop_queue = shop_queue
        self.items = []

    def run(self):
        '''
        ショップごとの商品を安い方から規定数保存
        '''
        print('[{}] Start Search Item Thread'.format(self.native_id))
        while True:
            if self.shop_queue.empty():
                time.sleep(10)
                continue

            shop = self.shop_queue.get()
            xlsx_fname = os.path.join(shop['shop_folder'], shop['shop_fname'])
            xlsx_wb = openpyxl.Workbook()
            xlsx_ws = xlsx_wb.active

            # initial request
            print('[{}] Initial Request {}'.format(self.native_id, shop['name']))
            params = create_query_params(self.appid, self.get_results,
                                {'seller_id': shop['seller_id'],
                                    'sort': '+price'})
            client = httpx.Client(params=params)
            r = client.get(url=itemSearch_ep)
            rdata = recieve_response(r, client)
            totalResults = rdata['totalResultsAvailable']
            print('[{}] {}, num: {}'.format(self.native_id, shop['name'], totalResults))

            # 店舗の商品を検索してxlsxへ保存
            # 商品名, 値段, 店舗のURL
            '''
            price_range = create_price_range({'appid': self.appid,
                                            'results': self.get_results,
                                            'seller_id': shop['seller_id']})
            '''
            checkedResults = 0
            if totalResults >= MAX_RETURNED_RESULTS:
                client_minus = httpx.Client(params={'appid': self.appid,
                                                    'results': self.get_results,
                                                    'seller_id': shop['seller_id'],
                                                    'sort': '-price'})
                r_minus = client_minus.get(url=itemSearch_ep)
                r_minusData = recieve_response(r_minus, client)
                pStart, pEnd = rdata['hits'][0]['price'], r_minusData['hits'][0]['price']
            else:
                pStart, pEnd = rdata['hits'][0]['price'], rdata['hits'][-1]['price']

            pFrom, pTo = pStart, pEnd
            while checkedResults < totalResults and checkedResults < MAX_ITEMS_NUM:
                params['start'] = 1
                availableResults = 0
                resultsSave = [] # [(availableResults, pFrom, pTo), ...]
                if totalResults >= 1000:
                    # 1000件以内の検索結果が収まるように検索クエリを調整
                    while True:
                        params['price_from'] = pFrom
                        params['price_to'] = pTo
                        client = httpx.Client(params=params)
                        r = client.get(url=itemSearch_ep)
                        rdata = recieve_response(r, client)
                        if not rdata:
                            return
                        availableResults = rdata['totalResultsAvailable']
                        if availableResults > 0:
                            resultsSave.append((availableResults, pFrom, pTo))

                        if availableResults == 0:
                            if resultsSave:
                                pFrom, pTo = pTo + 1, resultsSave[-1][2]
                            else:
                                pFrom, pTo = pTo + 1, pEnd
                        elif availableResults < 1000:
                            break
                        else:
                            pTo = (pFrom + pTo) // 2

                        if pFrom == params['price_to']:
                            print('[{}] cut same price.{}-{}.'.format(self.native_id, pFrom, pTo))
                            break
                        elif pTo <= pFrom:
                            pTo = pFrom
                else:
                    availableResults = totalResults

                pFrom, pTo = pTo + 1, pEnd # 次回用にアップデート
                if resultsSave:
                    rs_reverse = resultsSave[::-1]
                    print(rs_reverse)
                    for rs in rs_reverse:
                        if rs[0] - availableResults > 0:
                            print('[+] set   pTo=', rs[2], rs)
                            pTo = rs[2]
                            break
                        else:
                            print('[+] set pFrom=', rs[2]+1, rs)
                            pFrom = rs[2] + 1

                while params['start'] < availableResults \
                        and params['start'] < MAX_RETURNED_RESULTS\
                        and checkedResults < MAX_ITEMS_NUM:
                    client = httpx.Client(params=params)
                    r = client.get(url=itemSearch_ep)
                    rdata = recieve_response(r, client)
                    if not rdata:
                        return False
                    rReturned = rdata['totalResultsReturned']
                    hits = rdata['hits']
                    for hit in hits:
                        checkedResults += 1
                        name = hit['name']
                        price = hit['price']
                        xlsx_ws['A' + str(checkedResults)] = name
                        xlsx_ws['B' + str(checkedResults)] = price
                        xlsx_ws['C' + str(checkedResults)] = shop['url']
                        if checkedResults >= MAX_ITEMS_NUM:
                            xlsx_wb.save(xlsx_fname)
                            break
                    params['start'] += self.get_results
                    if params['start'] + self.get_results > MAX_RETURNED_RESULTS:
                        params['results'] = MAX_RETURNED_RESULTS - params['start']
                params['results'] = self.get_results
                xlsx_wb.save(xlsx_fname)
                if pFrom > pEnd:
                    break



class SearchShops(threading.Thread):
    def __init__(self, appid, rData, keyword, keyword_folder, shop_queue:queue.Queue):
        super(SearchShops, self).__init__()
        self.appid = appid
        self.rData = rData
        self.get_results = 100
        self.shops = {}
        self.keyword = keyword
        self.keyword_folder = keyword_folder
        self.shop_queue = shop_queue # SearchItemsOfShop にショップ情報を渡すキュー

        self.xlsx_fname = os.path.join(self.keyword_folder, 'shops.xlsx')
        self.xlsx_wb = openpyxl.Workbook()
        self.xlsx_ws = self.xlsx_wb.active
        # 最初のデータのseller情報をショップ情報のスクレイプングスレッドへ投げておく
        for hit in rData['hits']:
            seller = hit['seller']
            seller_id = seller['sellerId']
            if seller_id not in self.shops.keys():
                self.save_seller_info(seller)


    def save_seller_info(self, hit_seller):
        seller_name = hit_seller['name']
        seller_id = hit_seller['sellerId']
        seller_url = hit_seller['url']
        shop_fname = seller_name + '_' + seller_id + '.xlsx'
        shop_folder = os.path.join(self.keyword_folder, 'shop')

        self.shops[seller_id] = {
            'seller_id': seller_id,
            'name': seller_name,
            'url': seller_url,
            'keyword': self.keyword,
            'shop_folder': shop_folder,
            'shop_fname': shop_fname}
        self.shop_queue.put(self.shops[seller_id])
        # xlsxに追記
        # url, 店舗名, 店舗ごとのxlsxへのハイパーリンク
        self.xlsx_ws['A' + str(len(self.shops))] = seller_url
        self.xlsx_ws['B' + str(len(self.shops))] = seller_name
        self.xlsx_ws['C' + str(len(self.shops))].value = 'ファイルを開く'
        self.xlsx_ws['C' + str(len(self.shops))].hyperlink = os.path.join('shop', shop_fname)
        self.xlsx_wb.save(self.xlsx_fname)


    def run(self):
        '''
        Yahoo! Shoppingの検索結果は、1000件までしか取得できない (start + results <= 1000)
        なので、検索結果が1000件に絞られるように値段幅を変更して店舗を全件取得
        '''
        totalResults = self.rData['totalResultsAvailable']
        checkedResults = 0

        '''
        price_range = create_price_range(params={'appid': self.appid,
                                                'results': self.get_results,
                                                'query': self.keyword})
        '''
        if totalResults >= MAX_RETURNED_RESULTS:
            client_minus = httpx.Client(params={'appid': self.appid,
                                                'results': self.get_results,
                                                'sort': '-price',
                                                'query': self.keyword})
            r_minus = client_minus.get(url=itemSearch_ep)
            r_minusData = recieve_response(r_minus, client_minus)
            pStart, pEnd = self.rData['hits'][0]['price'], r_minusData['hits'][0]['price']
        else:
            pStart, pEnd = self.rData['hits'][0]['price'], self.rData['hits'][-1]['price']

        pFrom, pTo = pStart, pEnd
        while checkedResults < totalResults:
            availableResults = 0
            resultsSave = [] # [(availableResults, pFrom, pTo), ...]
            params = create_query_params(self.appid,
                                        self.get_results,
                                        {'query': self.rData['request']['query'],
                                        'sort': '+price',
                                        'start': 1})
            if totalResults >= 1000:
                while True:
                    params['price_from'] = pFrom
                    params['price_to'] = pTo
                    client = httpx.Client(params=params)
                    r = client.get(url=itemSearch_ep)
                    rdata = recieve_response(r, client)
                    availableResults = rdata['totalResultsAvailable']

                    if availableResults > 0:
                        resultsSave.append((availableResults, pFrom, pTo))

                    if availableResults == 0:
                        if resultsSave:
                            pFrom, pTo = pTo + 1, resultsSave[-1][2]
                        else:
                            pFrom, pTo = pTo + 1, pEnd
                    elif availableResults < 1000:
                        break
                    else:
                        pTo = (pFrom + pTo) // 2

                    if pFrom == params['price_to']:
                        print('[{}] cut same price. {}-{}.'.format(self.native_id, pFrom, pTo))
                        break
                    elif pTo <= pFrom:
                        pTo = pFrom
            else:
                availableResults = totalResults

            pFrom, pTo = pTo + 1, pEnd
            if resultsSave:
                rs_reverse = resultsSave[::-1]
                for rs in rs_reverse:
                    if rs[0] - availableResults > 0:
                        print('[+]   pTo=', rs[2], rs)
                        pTo = rs[2]
                        break
                    else:
                        print('[+] pFrom=', rs[2]+1, rs)
                        pFrom = rs[2] + 1

            # save shops
            while params['start'] < availableResults and params['start'] < MAX_RETURNED_RESULTS:
                print(params)
                client = httpx.Client(params=params)
                r = client.get(url=itemSearch_ep)
                rdata = recieve_response(r, client)
                if not rdata:
                    return False
                rReturned = rdata['totalResultsReturned']
                hits = rdata['hits']
                for hit in hits:
                    seller_id = hit['seller']['sellerId']
                    if seller_id not in self.shops.keys():
                        self.save_seller_info(hit['seller'])
                params['start'] += self.get_results
                if params['start'] + self.get_results > MAX_RETURNED_RESULTS:
                    params['results'] = MAX_RETURNED_RESULTS - params['start']
                    print('set results', params['results'])
                checkedResults += rReturned
            params['results'] = self.get_results
            if pFrom > pEnd:
                break
        print('[1] search shops finish: ', self.keyword, len(self.shops))
        return True


class searchItems:
    MAX_RETURNED_RESULTS = 1000 # Yahoo APIの制限。取得できる検索結果の上限
    def __init__(self, keywords:list, appids:list, output:str, max_number:int):
        self.keywords = keywords
        self.appids = appids
        self.appid = self.appids[0]
        self.output = output
        self.output_fname = 'out'
        self.max_number = max_number
        self.get_results = 100
        self.shops = {}
        self.results = {}
        self.tmr_cnt = 0 # 429: Too Many Requests を返却された回数


    def run(self):
        shop_queue = queue.Queue()

        # save items of each shop
        searchItemsOfShop = SearchItemOfShop(self.appids[-1], shop_queue)
        searchItemsOfShop.start()

        for keyword in self.keywords:
            print('[+]', keyword)
            keyword_folder = os.path.join(self.output,
                                            keyword,
                                            time.strftime('%Y%m%d_%H%M'))
            try:
                os.makedirs(keyword_folder, exist_ok=True)
                os.makedirs(os.path.join(keyword_folder, 'shop'), exist_ok=True)
            except Exception as e:
                print(e)
                return

            params = create_query_params(
                                self.appid, self.get_results,
                                {'query': keyword,
                                'sort': '+price'})
            client = httpx.Client(params=params)
            request = client.build_request(method='GET', url=itemSearch_ep, params=params)
            print('[+]Initial Request', request.url)
            r = client.send(request)
            #r = client.get(url=itemSearch_ep)
            rData = recieve_response(r, client)
            if not rData:
                return -1
            print('[+]Success: Initial Request')

            # save shops
            searchShopsThread = SearchShops(self.appids[0],
                                                rData, keyword,
                                                keyword_folder, shop_queue)
            searchShopsThread.start()

            while searchShopsThread.is_alive():
                time.sleep(60)
            print('[0] search keyword finish:', keyword)

        while searchItemsOfShop.is_alive():
            time.sleep(60)
