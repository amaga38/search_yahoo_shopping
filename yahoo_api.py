import httpx

itemSearch_ep = 'https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch'
max_rpm = 30 # max

class searchItems:
    def __init__(self, keywords:list, appids:list, output:str, max_number:int):
        self.keywords = keywords
        self.appids = appids
        self.appid = self.appids[0]
        self.output = output
        self.output_fname = 'out'
        self.max_number = max_number
        self.get_results = 90
        self.results = {}

    def __create_query_params(self, keyword):
        params = {'appid': self.appid,
                    'results': self.results,
                    'query': keyword}
        return params

    def __save_hits(self, hits:list):
        return

    def run(self):
        for keyword in self.keywords:
            print('[+]', keyword)
            save_info_count = 0
            while save_info_count < self.max_number:
                params = self.__create_query_params(keyword)
                print('[+]', params)
                r = httpx.get(url=itemSearch_ep, params=params)
                if r.status_code == 200:
                    print("Request Success")
                    rData = r.json()
                    print(rData['totalResultsAvailable'])
                    print(rData['totalResultsReturned'])
                    print(rData['firstResultsPosition'])
                elif r.status_code == 429:
                    # Too Many Requests
                    print("Error: Too Many Requests.")
                else:
                    print('Status Code:', r.status_code)
                    print(r.text)
                break # for test
            break # for test
