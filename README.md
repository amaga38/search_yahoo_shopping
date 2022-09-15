# search_yahoo_shopping
[Yahoo! JAPANの商品検索API(V3)](https://developer.yahoo.co.jp/webapi/shopping/shopping/v3/itemsearch.html)を利用してYahoo! ショッピングの店舗の商品を検索、保存するツールです。

キーワード検索 → ヒットした商品を出品している店舗の店舗ページで出品されている商品を**安い順**に昇順で、商品名、値段、店舗URLを記録します。また、検索にヒットした店舗一覧を別ファイルに記録します。

* out/キーワード/<時間_日付>/shop.xlsx: 店舗一覧のファイル。店舗名、店舗URL
* out/キーワード/<時間_日付>/shop/<ショップ名_ショップID>.xlsx: 店舗の出品商品一覧のファイル。商品名、値段、店舗URL

## 注意事項、制限事項
* [商品検索APIには1分間で30リクエストの制限があります](商品検索APIには1分間で30リクエストの制限があります)
* APIの仕様のため、商品の検索結果で取得できる検索結果は、**1000件が上限**です。同一の値段で1000件以上の商品が出品されていると、すべての商品を記録することができません

## インストール

動作確認環境 Windows 11 Home 21H2、Python 3.9.0

事前に [Python](https://www.python.org/) 3.9.0 以上のバージョンをインストール

プログラムのダウンロード: [GitHub の Zip リンク](https://github.com/amaga38/search_yahoo_shopping/archive/refs/heads/main.zip)

- 解凍したフォルダを開き、フォルダーのアドレス欄に`cmd`と入力して、Enter。コマンドターミナルを開く
- コマンドターミナルで以下のコマンドを実行して、必要な外部ライブラリをインストール

```
$ pip install -r requirements.txt
```

## 実行前の準備
`search_yahoo_shopping.py`と同じフォルダに以下のファイルを用意
* appid.xlsx
* keyword.xlsx

#### appid.xlsx
* Yahoo! Japan Web APIを利用するために必要なアプリケーションIDを記載するファイル。プログラムを動かすためには2個のIDが必要
* [Yahoo! JAPANの開発者ページ](https://e.developer.yahoo.co.jp/dashboard/)でアプリを2個登録する
* 「新しいアプリケーションを登録」→ 「ID連携を利用しない」でアプリケーションを登録。ID連携以外は利用者の情報を入力
* コピペでID最後のハイフン`-`が抜けやすいので注意

#### keyword.xlsx
* 検索するキーワードをA列にそれぞれ記載したファイル
* 1行1キーワードになります


## 実行

```
python search_yahoo_shopping.py
```

keyword.xlsx に記載されたキーワードを上から順番に検索し、店舗の出品商品情報を記録していきます。

## プログラムについて

