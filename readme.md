# odtiles-base
オンデマンド型のXYZタイル地図およびWMSを提供するサービス   
タイル画像生成およびWMS画像生成は、gdalwarpを使用している

## システム構成
- djangoを使用したWebアプリケーション
- DockerComposeで配置されるアプリケーションのルートフォルダ
    - `/opt/odtiles`
- DockerComposeで配置されるログフォルダ
    - `/opt/odtiles/logs`
    - odtiles/uwsgi.ini で設定
- タイルソースフォルダ
    - `/mnt/odtiles/tilesrc`
    - XYZタイルおよびWMSのソース画像を配置する場所
    - サブフォルダを任意の階層で作成可能
    - GeoTIFFファイルを配置する
    - ファイル拡張子は`.tif` 
    - `odtiles/settings.py` で設定 
- タイル出力フォルダ
    - `/mnt/odtiles/tileout`
    - 生成したタイル画像の保存先
    - 画像キャッシュとしても使用される
    - 定期的な削除が必要
    - `odtiles/settings.py` で設定
- ＷＭＳ出力フォルダ
    - `/mnt/odtiles/wmsout`
    - 生成したWMS画像の保存先
    - 画像キャッシュとしても使用される
    - 定期的な削除が必要
    - `odtiles/settings.py` で設定

## 環境設定

djangoの設定ファイル（`odtiles/settings.py`）から環境設定をしている


- URL
    - 外部からアクセスするときのURLを設定する
    - WMSのGepCapabilitiesの応答で使用する
- UPLOAD_API_TOKEN
    - upload APIと、setCapabilities API を使用するときに指定するトークン
- TILE_SOURCE_FOLDER
    - タイルおよびWMSの元になる画像を格納するフォルダ 
- TILE_OUTPUT_FOLDER
    - タイル画像出力のキャッシュフォルダ
- WMS_OUTPUT_FOLDER
    - WMS画像出力のキャッシュフォルダ
- MAX_AGE
    - ブラウザキャッシュの寿命（通常画像）
- MAX_AGE_LIVE
    - ブラウザキャッシュの寿命（ライブフォルダの画像）

## UPLOAD APIトークン
- アップロードAPIを使用するためのトークンは、コンテナの初回起動時に`init_token.py`により設定される
- Dockerのログもしくはsettings.pyを開いて確認する
## XYZタイルのURL
URLは、`http(s)://<ドメイン名>/xyz/<サブフォルダを任意に設定できる>/{z}/{x}/{y}.png`
- タイル座標は左上原点
- タイルURLのサブフォルダは`<TILE_SOURCE_FOLDER>`のサブフォルダとGeoTIFFのファイル名で決まる

  

## アップロードAPI
GeoTIFFファイルをアップロードする
- POSTで `/upload/` にリクエストを送信する
- リクエストヘッダに `token` を指定する
- リクエストにGeoTIFFファイルを添付する（名称：file）
- トークンは、`odtiles/settings.py` の `UPLOAD_API_TOKEN` で設定する（設定されていない場合、アップロードAPIは動作しない）
- アップロードURLのサブフォルダが、tilesrcフォルダのサブフォルダに対応する

### 例
以下のURLに、ファイル名`sample.tif`をアップロードした場合
- `http(s):<ドメイン名>/upload/aaa/bbb` 

XYZタイルのURLは以下になる
- `http(s)://<ドメイン名>/xyz/aaa/bbb/sample/{z}/{x}/{y}.png`

アップロードしたファイルが格納される場所は以下になる
- `<TILE_SOURCE_FOLDER>/aaa/bbb/sample.tif`

#### curl コマンドの例
```
curl -X POST http(s)://<サーバー名>/upload/aaa/bbb/ \
    -H "token:<UPLOAD_API_TOKEN>" \
    -F "file=@/my/file/path/sample.tif"
```

## WMS有効化API
アップロードしたGeoTIFFファイルのWMSを有効にする

- POSTで`setCapabilities`にリクエストを送信する
- リクエストヘッダに`token`を指定する
- リクエストボディにCapabilities情報をJSONで指定する
- トークンは、`odtiles/settings.py` の `UPLOAD_API_TOKEN` で設定する（設定されていない場合、WMS有効化APIは動作しない）
- アップロードURLのサブフォルダが、tilesrcフォルダのサブフォルダに対応する
- apikeyでアクセス制限を付けると、XYZタイルも同じapikeyで制限が付く

### 例
XYZタイルのURLが以下のデータに対して、WMSを設定する場合は
- `http(s)://<ドメイン名>/xyz/aaa/bbb/sample/{z}/{x}/{y}.png`

以下のURLにCapabilities情報をPOSTする
- `http(s)://<ドメイン名>/setCapabilities/aaa/bbb/sample`
  
### Capabilities情報
以下の項目を持つオブジェクトを指定する
| 項目名    | 型     | 説明                | 必須 |
| :-------- | :----- | :------------------ | :--- |
| name      | string | 名称（レイヤ名称）  | -    |
| legendUrl | string | 凡例画像のURL       | -    |
| apikey | string | XYZタイル画像のアクセスおよびWMSのGetMapのアクセスを制限するために設定する<br>apikeyがないCapabilities情報をPOSTすることで制限を解除できる<br>※upload, setCapabilitiesで使用するtokenとは別 | - |

#### Capabilities情報の記述例
```
{
    "name" : "サンプルレイヤ",
    "legendUrl" : "https://example.jp/my/legend/image.png"
    "apikey" : "abc"
}
```

#### curl コマンドの例
```
curl -X POST http(s)://<ドメイン名>/setCapabilities/aaa/bbb/ \
    -H "token:<UPLOAD_API_TOKEN>" \
    -d '{"name": "サンプルレイヤ", "legendUrl": "https://example.jp/my/legend/image.png"}'
```
このときのGetCapabilitiesのURLは以下になる  
```
http(s)://<ドメイン名>/wms/aaa/bbb/sample?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1
```

## WMSを無効にするAPI
空のCapabilities情報をPOSTすることでWMSを無効にできる（同時にapikeyによるアクセス制限も解除される）

#### curl コマンドの例
```
curl -X POST http(s)://<サーバー名>/setCapabilities/aaa/bbb/ \
    -H "token:<UPLOAD_API_TOKEN>" \
    -d '{}'
```
-----
## Dockerイメージ
- [take4iso/odtiles-base](https://hub.docker.com/r/take4iso/odtiles-base)