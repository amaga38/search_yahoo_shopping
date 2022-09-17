
import time
import httpx
from bs4 import BeautifulSoup


class HttpClient(httpx.Client):
    # Yahoo! APIに合わせて1分30リクエストまでに制限する
    # 実装上は、前のリクエストから2秒経過していたら送信する
    TIME_WAIT_MS = 2000
    MAX_RETRY = 5
    def __init__(self):
        super().__init__()
        self.last_req_utime = 0
        self.req_cnt = 0

    def __wait_request(self):
        tdiff = time.time() - self.last_req_utime
        if tdiff < self.TIME_WAIT_MS:
            _wait = (self.TIME_WAIT_MS - tdiff) / 1000
            time.sleep(_wait)
        self.last_req_utime = time.time()


    def get(self, url:str, params):
        self.__wait_request()
        r = super().get(url=url, params=params)
        if r.status_code != 200:
            for _ in range(self.MAX_RETRY):
                self.__wait_request()
                r = super().get(url=url, params=params)
                if r.status_code == 200:
                    break
            if r.status_code != 200:
                raise RuntimeError
        return r


def get_item_list(html):
    item_list = [] # [(name, link, price), ...]
    soup = BeautifulSoup(html, 'html.parser')
    ul = soup.select('.mdSearchResult > ul.elItems > li.elItem')
    if not ul:
        # 検索結果なし
        return []
    for idx, li in enumerate(ul):
        item_name = li.select_one('div.elName > a.elNameLink')
        item_link = item_name.attrs['href']
        item_price = li.select_one('div.elPriceItem > span.elPriceValue')
        item_price = item_price.next_element
        new_elm = {'name': item_name.text.strip('\n'),
                    'item_url': item_name.attrs['href'],
                    'price': item_price.replace(',', '')}
        item_list.append(new_elm)
    return item_list


def scraipe_yahoo_shopsite(url, pFrom=0, pTo=0):
    # Yahoo!ショッピングのショップ個別サイトの商品一覧情報を取得
    # 
    item_list = []
    MAX_PAGE = 29

    _url = httpx.URL(url)
    search_url = _url.scheme + '://' + _url.host + _url.path + 'search.html'
    params = {'p': '',
                'n': 100, # 商品表示数
                'X': 2   # 安い順（値段昇順）
                }
    if pFrom:
        params['pf'] = pFrom
    if pTo:
        params['pt'] = pTo

    client = HttpClient()
    r = client.get(url=search_url, params=params)
    item_list += get_item_list(r.text)
    for i in range(1, MAX_PAGE):
        params['page'] = i
        r = client.get(url=search_url, params=params)
        t = get_item_list(r.text)
        if not t:
            break
        item_list += t
    return item_list


def test():
    shop_url = 'https://store.shopping.yahoo.co.jp/bearfoot-shoes/?sc_i=shp_pc_search_itemlist_shsrg_strnm'
    r = scraipe_yahoo_shopsite(shop_url, 1200, 1300)
    return 0


if __name__ == '__main__':
    exit(test())
