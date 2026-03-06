# アプリケーション全体用のライブラリ
import os, re, math, json
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from osgeo import gdal, osr

gdal.UseExceptions()

originShift = 20037508.342789244
MAX_MERCATOR_LAT = 85.051129  # Webメルカトルの最大緯度

# 緯度をWebメルカトルの有効範囲にクリップ
def clampLatitude(lat):
    """Clamp latitude to valid Web Mercator bounds"""
    return max(-MAX_MERCATOR_LAT, min(MAX_MERCATOR_LAT, lat))


# GeoTIFFの範囲（bbox)をEPSG:4326とEPSG:3857で取得する
def getBbox(filepath: str):
    """GeoTIFFの範囲（bbox)をEPSG:4326とEPSG:3857で取得する"""
    if not os.path.exists(filepath):
        return None
    ds = gdal.Open(filepath)
    gt = ds.GetGeoTransform()
    width = ds.RasterXSize
    height = ds.RasterYSize

    # 回転付きGeoTransformにも対応した四隅座標を計算
    ul = (gt[0], gt[3])
    ur = (gt[0] + width * gt[1], gt[3] + width * gt[4])
    ll = (gt[0] + height * gt[2], gt[3] + height * gt[5])
    lr = (gt[0] + width * gt[1] + height * gt[2], gt[3] + width * gt[4] + height * gt[5])

    # まずEPSG:4326に変換（GDAL3以降の軸順序差異を吸収するためGIS順序を固定）
    src_srs = osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())
    wgs84_srs = osr.SpatialReference()
    wgs84_srs.ImportFromEPSG(4326)
    src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    wgs84_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_wgs84 = osr.CoordinateTransformation(src_srs, wgs84_srs)

    ul_wgs84 = to_wgs84.TransformPoint(*ul)
    ur_wgs84 = to_wgs84.TransformPoint(*ur)
    ll_wgs84 = to_wgs84.TransformPoint(*ll)
    lr_wgs84 = to_wgs84.TransformPoint(*lr)

    # 緯度をWebメルカトルの有効範囲にクリップ
    ul_clamped = (ul_wgs84[0], clampLatitude(ul_wgs84[1]))
    ur_clamped = (ur_wgs84[0], clampLatitude(ur_wgs84[1]))
    ll_clamped = (ll_wgs84[0], clampLatitude(ll_wgs84[1]))
    lr_clamped = (lr_wgs84[0], clampLatitude(lr_wgs84[1]))

    lon_min = min(ul_clamped[0], ur_clamped[0], ll_clamped[0], lr_clamped[0])
    lat_min = min(ul_clamped[1], ur_clamped[1], ll_clamped[1], lr_clamped[1])
    lon_max = max(ul_clamped[0], ur_clamped[0], ll_clamped[0], lr_clamped[0])
    lat_max = max(ul_clamped[1], ur_clamped[1], ll_clamped[1], lr_clamped[1])
    latlon_bbox = [lon_min, lat_min, lon_max, lat_max]

    # EPSG:3857に変換
    mercator_srs = osr.SpatialReference()
    mercator_srs.ImportFromEPSG(3857)
    mercator_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_mercator = osr.CoordinateTransformation(wgs84_srs, mercator_srs)
    
    ul_mercator = to_mercator.TransformPoint(*ul_clamped)
    ur_mercator = to_mercator.TransformPoint(*ur_clamped)
    ll_mercator = to_mercator.TransformPoint(*ll_clamped)
    lr_mercator = to_mercator.TransformPoint(*lr_clamped)

    x_min = min(ul_mercator[0], ur_mercator[0], ll_mercator[0], lr_mercator[0])
    y_min = min(ul_mercator[1], ur_mercator[1], ll_mercator[1], lr_mercator[1])
    x_max = max(ul_mercator[0], ur_mercator[0], ll_mercator[0], lr_mercator[0])
    y_max = max(ul_mercator[1], ur_mercator[1], ll_mercator[1], lr_mercator[1])

    mercator_bbox = [x_min, y_min, x_max, y_max]

    return latlon_bbox, mercator_bbox

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


#GeoTIFFの情報ファイルを生成する
def createInfoFile(sourceFile):
    if not os.path.exists(sourceFile):
        return None
    latlon_bbox, mercator_bbox = getBbox(sourceFile)

    info = {
        'lonlatBbox': latlon_bbox,
        'mercatorBbox': mercator_bbox
    }
    infoFile = f'{sourceFile}.info.json'
    with open(infoFile, 'w') as f:
        json.dump(info, f)
    return info

# GeoTIFFの情報ファイルを取得する
def getInfoFile(sourceFile):
    infoFile = f'{sourceFile}.info.json'
    if not os.path.exists(infoFile):
        #ないので作る
        return createInfoFile(sourceFile)
    with open(infoFile, 'r') as f:
        info = json.load(f)
    return info

# BBOX同士が重なっているかを判定する
def isBboxOverlap(bbox1, bbox2):
    """BBOX同士が重なっているかを判定する"""
    if bbox1[0] >= bbox2[2] or bbox1[2] <= bbox2[0]:
        return False
    if bbox1[1] >= bbox2[3] or bbox1[3] <= bbox2[1]:
        return False
    return True