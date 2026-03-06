# アプリケーション全体用のライブラリ
import os, re, math, json
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from osgeo import gdal, osr

gdal.UseExceptions()

originShift = 20037508.342789244

# GeoTIFFの範囲（bbox)をEPSG:4326で取得する
def getLonlatBbox(filepath: str):
    """GeoTIFFの範囲（bbox)をEPSG:4326で取得する"""
    if not os.path.exists(filepath):
        return None
    ds = gdal.Open(filepath)
    gt = ds.GetGeoTransform()
    width = ds.RasterXSize
    height = ds.RasterYSize
    
    # 四隅の座標を計算
    ul = (gt[0], gt[3])                                     # 左上
    ur = (gt[0] + gt[1] * width, gt[3])                     # 右上
    ll = (gt[0], gt[3] + gt[5] * height)                    # 左下
    lr = (gt[0] + gt[1] * width, gt[3] + gt[5] * height)    # 右下
    
    # EPSG4326に変換
    src_srs = osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromEPSG(4326)
    transform = osr.CoordinateTransformation(src_srs, dst_srs)
    ul_wgs84 = transform.TransformPoint(*ul)
    ur_wgs84 = transform.TransformPoint(*ur)
    ll_wgs84 = transform.TransformPoint(*ll)
    lr_wgs84 = transform.TransformPoint(*lr)

    x_min = min(ul_wgs84[0], ur_wgs84[0], ll_wgs84[0], lr_wgs84[0])
    y_min = min(ul_wgs84[1], ur_wgs84[1], ll_wgs84[1], lr_wgs84[1])
    x_max = max(ul_wgs84[0], ur_wgs84[0], ll_wgs84[0], lr_wgs84[0])
    y_max = max(ul_wgs84[1], ur_wgs84[1], ll_wgs84[1], lr_wgs84[1])

    return [x_min, y_min, x_max, y_max]

# WebメルカトルのX,Y,Zoomからメルカトル座標のBBOXを計算する
def xyzToMercatorBbox(x, y, zoom):
    """Convert XYZ tile coordinates to Mercator bbox"""
    initialResolution = 2 * originShift / 256
    resolution = initialResolution / (2 ** zoom)

    minX = x * 256 * resolution - originShift
    maxY = originShift - y * 256 * resolution
    maxX = (x + 1) * 256 * resolution - originShift
    minY = originShift - (y + 1) * 256 * resolution

    return [minX, minY, maxX, maxY]

# GDALのWARPでタイル画像を生成する
def generateImage(bbox, width, height, sourceFile, outFile):
    """WMS画像を生成する"""
    #ソースファイルがあるか？
    if not os.path.exists(sourceFile):
        return False
        
    # GDALを使用してWMS画像を生成
    dst_ds = gdal.Warp(
        outFile,
        sourceFile,
        format='PNG',
        outputBounds=bbox,
        width=width,
        height=height,
        dstSRS='EPSG:3857',
        resampleAlg='bilinear'
    )
    # データセットが作成されたか確認
    if dst_ds is None:
        return False
    # データセットを明示的に閉じて、書き込みが完了するまで待つ
    dst_ds.FlushCache()
    dst_ds = None
    # ファイルが実際に作成されたか確認
    if not os.path.exists(outFile):
        return False
    return True


# キーファイルを設定する
def setKeyFile(apikey: str, srcfile: str):
    """APIキーがない場合はキーファイルを削除する。APIキーがある場合はキーファイルに書き込む。"""
    if not os.path.exists(srcfile):
        return False
    keyfile = f'{srcfile}.apikey'
    if apikey is None or apikey == '':
        if os.path.exists(keyfile):
            os.remove(keyfile)
        return True
    with open(keyfile, 'w', encoding='utf-8') as f:
        f.write(apikey.strip())
    return True

# キーファイルを読み込む
def getKeyFromFile(srcfile: str):
    """キーファイルからAPIキーを読み込む。キーファイルがない場合はNoneを返す。"""
    keyfile = f'{srcfile}.apikey'
    if not os.path.exists(keyfile):
        return None
    with open(keyfile, 'r', encoding='utf-8') as f:
        apikey = f.read().strip()
    return apikey

# wms.xmlファイルを設定する
def setWmsXmlFile(data, srcfile):
    """WMSのXMLファイルを設定する。dataがNoneの場合はXMLファイルを削除する。dataがある場合はXMLファイルに書き込む。"""
    if not os.path.exists(srcfile):
        return False
    wmsfile = f'{srcfile}.wms.xml'
    if data is None:
        if os.path.exists(wmsfile):
            os.remove(wmsfile)
        return True
    with open(wmsfile, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return True