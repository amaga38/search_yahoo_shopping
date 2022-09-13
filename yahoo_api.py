import time
import httpx

import queue
import threading

itemSearch_ep = 'https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch'
max_rpm = 30 # max requests per minute

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
    return None


def recieve_response(r:httpx.Response, client: httpx.Client):
    if r.status_code == 200:
        rData = r.json()
        print('[+]Check results:', rData['totalResultsAvailable'], rData['totalResultsReturned'], rData['firstResultsPosition'])
        return r.json()
    elif r.status_code == 429:
        # Too Many Requests
        print("[-]Error: Too Many Requests.")
        r = retry_request(client)
        if not r:
            print('[-] Too Many Request')
            return None
        return r.json()
    else:
        print('Status Code:', r.status_code, ', Text:', r.text)
        return None


class SearchShops(threading.Thread):
    def __init__(self, appid, rData):
        self.appid = appid
        self.rData = rData

    def run(self):
        return


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


    def __save_hits_shops(self, rData: dict):
        '''
        Yahoo! Shoppingの検索結果は、1000件までしか取得できない (start + results <= 1000)
        なので、検索結果が1000件に絞られるように値段幅を変更して店舗を全件取得
        '''
        totalResults = rData['totalResultsAvailable']
        checkedResults = 0
        pFrom, pTo = 1, 1000 # 初期値
        while checkedResults < totalResults:
            availableResults = 0
            while True:
                params = create_query_params(self.appid,
                                    self.get_results,
                                    {'query': rData['request']['query'],
                                    'price_from': pFrom,
                                    'price_to': pTo
                                    })
                client = httpx.Client(params=params)
                r = client.get(url=itemSearch_ep)
                rdata = recieve_response(r, client)
                availableResults = rdata['totalResultsAvailable']
                if availableResults == 0:
                    pFrom, pTo = pTo + 1, pTo + 1000
                elif availableResults <= 1000:
                    break
                else:
                    pTo = (pFrom + pTo) // 2
                if pTo <= pFrom:
                    break

            pFrom, pTo = pTo + 1, pTo + 1000
            # save shops
            params['start'] = 1
            while params['start'] < availableResults:
                print(params)
                client = httpx.Client(params=params)
                r = client.get(url=itemSearch_ep)
                rdata = recieve_response(r, client)
                if not rdata:
                    return False
                rReturned = rdata['totalResultsReturned']
                hits = rdata['hits']
                for hit in hits:
                    name = hit['seller']['name']
                    self.shops[name] = {
                            'sellerId': hit['seller']['sellerId'],
                            'url': hit['seller']['url']}
                params['start'] += self.get_results
                if params['start'] + self.get_results > self.MAX_RETURNED_RESULTS:
                    params['results'] = self.MAX_RETURNED_RESULTS - params['start']
                    print('set results', params['results'])
                checkedResults += rReturned
            params['results'] = self.get_results
        return True


    def run(self):
        for keyword in self.keywords:
            print('[+]', keyword)
            save_info_count = 0

            print('[+]Initial Request')
            params = create_query_params(
                                self.appid, self.get_results,
                                {'query': keyword})
            client = httpx.Client(params=params)
            r = client.get(url=itemSearch_ep)
            if not recieve_response(r, client):
                return -1
            print('[+]Success: Initial Request')

            # save shops
            if not self.__save_hits_shops(r.json()):
                return -1
            print(self.shops)
            break
            while save_info_count < self.max_number:
                print('[+]', params)
                r = client.get(url=itemSearch_ep)
                if not self.__recieve_response(r, client):
                    break
                print('Success')
                break # for test
            break # for test
