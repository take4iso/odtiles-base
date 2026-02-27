# odtiles-base
オンデマンド型のXYZタイル地図およびWMSを提供するサービス   
タイル生成は、gdal2tilesにパッチを当てた[gdal2tiles.py](https://github.com/take4iso/gdal2tiles)を使用している（詳細はgdal2tilesのREADME）  

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
URLは、`http(s)://<サーバー名>/xyz/<サブフォルダを任意に設定できる>/{z}/{x}/{-y}.png`
- タイル座標は左下原点。
- タイルURLのサブフォルダは`<TILE_SOURCE_FOLDER>`のサブフォルダとGeoTIFFのファイル名で決まる
### 例
ソースフォルダに以下のGeoTIFFファイルがあるとした場合
- `<TILE_SOURCE_FOLDER>/aaa/bbb/sample.tif`
  
タイルのURLは以下のようになる
- `http(s)://<サーバー名>/xyz/aaa/bbb/sample/{z}/{x}/{-y}.png`

## アップロードAPI
GeoTIFFファイルをアップロードする
- POSTで `/upload/` にリクエストを送信する
- リクエストヘッダに `token` を指定する
- リクエストにGeoTIFFファイルを添付する（名称：file）
- アップロードAPIトークンは、`odtiles/settings.py` の `UPLOAD_API_TOKEN` で設定する
- アップロードURLのサブフォルダが、tilesrcフォルダのサブフォルダに対応する

`http(s)://<ドメイン名>/upload/aaa/bbb` に対して、sample.tifファイルをポストした場合、  
`<TILE_SOURCE_FOLDER>/aaa/bbb/sample.tif` にファイルが格納される

上記のsample.tifに対するXYZタイルマップのURLは以下になる
`http(s)://<ドメイン名>/xyz/aaa/bbb/sample/{z}/{x}/{-y}.png`

#### curl コマンドの例
```
curl -X POST http(s)://<サーバー名>/upload/aaa/bbb/ \
    -H "token:<UPLOAD_API_TOKEN>" \
    -F "file=@/my/file/path/sample.tif"
```

## WMSを有効化するAPI
アップロードしたGeoTIFFファイルのWMSを有効にする

- POSTで`setCapabilities`にリクエストを送信する
- リクエストヘッダに`token`を指定する
- リクエストボディにCapabilities情報をJSONで指定する
- アップロードAPIトークンは、`odtiles/settings.py` の `UPLOAD_API_TOKEN` で設定する
- アップロードURLのサブフォルダが、tilesrcフォルダのサブフォルダに対応する

### Capabilities情報
`layers`の名称の配列に、以下の項目を持つオブジェクトを列挙する（複数指定可能）
| 項目名    | 型     | 説明                | 必須 |
| :-------- | :----- | :------------------ | :--- |
| file      | string | GeoTIFFのファイル名 | ✔    |
| name      | string | 名称（レイヤ名称）  | ✔    |
| legendUrl | string | 凡例画像のURL       | -    |

#### Capabilities情報の記述例
```
{
    "layers" : [
        {
            "file" : "sample.tif",
            "name" : "サンプルレイヤ",
            "legendUrl" : "https://sample.jp/my/legend/image.png"
        }
    ]
}
```

#### curl コマンドの例
```
curl -X POST http(s)://<サーバー名>/setCapabilities/aaa/bbb/ \
    -H "token:<UPLOAD_API_TOKEN>" \
    -d '{"layers": [{"file": "sample.tif", "name": "サンプルレイヤ", "legendUrl": "https://sample.jp/my/legend/image.png"}]}'
```
このときのGetCapabilitiesのURLは、  
`http(s)://<サーバー名>/wms/aaa/bbb/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1`

## WMSを無効にするAPI
layers配列のないCapabilities情報をPOSTすることでWMSを無効にできる

#### curl コマンドの例
```
curl -X POST http(s)://<サーバー名>/setCapabilities/aaa/bbb/ \
    -H "token:<UPLOAD_API_TOKEN>" \
    -d '{"layers": []}'
```
-----
## Dockerイメージ
- [take4iso/odtiles-base](https://hub.docker.com/r/take4iso/odtiles-base)