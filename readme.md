# odtiles-base
オンデマンド型のXYZタイル地図を提供するサービス   
タイル生成は、gdal2tilesにパッチを当てた[gdal2tiles.py](https://github.com/take4iso/gdal2tiles)を使用している（詳細はgdal2tilesのREADME）  

## システム構成
- djangoを使用したWebアプリケーション
- uwsgi, ポート番号8080
- アプリケーションルートフォルダ
    - `/opt/odtiles`
- ログフォルダ
    - `/opt/odtiles/logs`
    - odtiles/uwsgi.ini で設定
- タイルソースフォルダ
    - `/mnt/odtiles/tilesrc`
    - XYZタイルのソース画像を配置する場所
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
## タイルのURL
- タイルのURLは、`http(s)://<サーバー名>/xyz/<サブフォルダを任意に設定できる>/{z}/{x}/{-y}.png`
- タイル座標は左下原点。
- タイルURLのサブフォルダはtilesrcフォルダ内のサブフォルダとGeoTIFFのファイル名で決まる
### 例
- tilesrcフォルダに以下のGeoTIFFファイルがあるとした場合
    - `/mnt/odtiles/tilesrc/2023/01/01/sample.tif`
- タイルのURLは以下のようになる
    - `http(s)://<サーバー名>/xyz/2023/01/01/sample/{z}/{x}/{-y}.png`
- タイル画像のMAX_AGEは、`odtiles/settings.py` で設定されている
    - `TILE_MAX_AGE`（デフォルトは86400秒）
- ライブタイルについて
    - 短時間で更新されるタイル画像のこと
    - サブフォルダに `/live/` または `/LIVE/` を含む場合、ライブタイルとして扱われる
    - ライブタイルのMAX_AGEは、`odtiles/settings.py` で設定されている
    - `TILE_MAX_AGE_LIVE`（デフォルトは60秒）
    - tilesrc のGeoTIFFファイルを上書き更新すると、タイルキャッシュ画像が更新される
## アップロードAPI
- タイルソースフォルダにGeoTIFFファイルをアップロードするAPI
- アップロードAPIは、POSTメソッドで `/upload/` エンドポイントにリクエストを送信する
- リクエストヘッダに `token` を含める
- リクエストボディにGeoTIFFファイルを含める（名称：file）
- アップロードAPIトークンは、`odtiles/settings.py` の `UPLOAD_API_TOKEN` で設定する
- アップロードURLのサブフォルダが、tilesrcフォルダのサブフォルダに対応する
- アップロードURLのサブフォルダは、任意の階層で設定可能
### 例
- タイルソースフォルダに以下のGeoTIFFファイルをアップロードする場合は、
    - `/mnt/odtiles/tilesrc/2023/01/01/sample.tif`
- アップロードAPIのURLは以下のようになる
    - `http(s)://<サーバー名>/upload/2023/01/01/`
    - curl コマンドの例
    ```bash
    curl -X POST http(s)://<サーバー名>/upload/2023/01/01/ \
        -H "token:<UPLOAD_API_TOKEN>" \
        -F "file=@/my/file/path/sample.tif"
    ```
## Dockerイメージ
- [take4iso/odtiles-base](https://hub.docker.com/r/take4iso/odtiles-base)