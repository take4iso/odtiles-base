# アプリケーション全体用のライブラリ
import os, re, math, json
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from osgeo import gdal

gdal.UseExceptions()

originShift = 20037508.342789244


# GeoTIFFの情報を取得する
def getGeotiffInfo(sourceFile):
    """infoファイルを作成する"""
    if not os.path.exists(sourceFile):
        return None
    stime = os.path.getmtime(sourceFile)
    # GeoTIFFの範囲（bbox）を取得する
    ds = gdal.Open(sourceFile)
    gt = ds.GetGeoTransform()
    x_min = gt[0]
    y_max = gt[3]
    x_max = x_min + gt[1] * ds.RasterXSize
    y_min = y_max + gt[5] * ds.RasterYSize
    #メルカトル座標に変換
    minX = x_min * originShift / 180.0
    minY = math.log(math.tan((90 + y_min) * math.pi / 360.0)) * originShift / math.pi
    maxX = x_max * originShift / 180.0
    maxY = math.log(math.tan((90 + y_max) * math.pi / 360.0)) * originShift / math.pi
    srcbbox = [minX, minY, maxX, maxY]
    lonlat_bbox = mercatorBboxToLonlatBbox(srcbbox)
    # ピクセルサイズを取得
    pixel_width = abs(gt[1])
    pixel_height = abs(gt[5])
    # infoファイルを書き込む
    info = {
        'bbox': srcbbox,
        'lonlat_bbox': lonlat_bbox,
        'filestamp': stime,
        'pixel_width': pixel_width,
        'pixel_height': pixel_height,
        'raster_size': {
            'width': ds.RasterXSize,
            'height': ds.RasterYSize
        }
    }
    return info

# 2つのbboxが重なっているかを判定する
def isBboxOverlap(bbox1, bbox2, pixel_width=0.0, pixel_height=0.0):
    """2つのbboxが重なっているかを判定する
    
    Args:
        bbox1: [min_x, min_y, max_x, max_y]
        bbox2: [min_x, min_y, max_x, max_y]
        pixel_width: ピクセルサイズ（X方向、許容マージン用）
        pixel_height: ピクセルサイズ（Y方向、許容マージン用）
    
    Returns:
        True: 重なっている、False: 重なっていない
    """
    # マージンを設定（ピクセルサイズを参考にしたマージン）
    margin_x = pixel_width if pixel_width > 0 else 0.0
    margin_y = pixel_height if pixel_height > 0 else 0.0
    
    # マージンを適用した判定
    if (bbox1[0] - margin_x >= bbox2[2] + margin_x or 
        bbox1[2] + margin_x <= bbox2[0] - margin_x or 
        bbox1[1] - margin_y >= bbox2[3] + margin_y or 
        bbox1[3] + margin_y <= bbox2[1] - margin_y):
        return False
    return True

# XYZからメルカトル座標のBBOXを計算する
def xyzToMercatorBbox(x, y, z):
    initialResolution = 2 * originShift / 256
    resolution = initialResolution / (2 ** z)

    minX = x * 256 * resolution - originShift
    maxY = originShift - y * 256 * resolution
    maxX = (x + 1) * 256 * resolution - originShift
    minY = originShift - (y + 1) * 256 * resolution

    return [minX, minY, maxX, maxY]

# メルカトル座標のBBOXから経度緯度のBBOXを計算する
def mercatorBboxToLonlatBbox(bbox):
    minX = bbox[0] / originShift * 180.0
    minY = math.atan(math.exp(bbox[1] / originShift * math.pi)) * 360.0 / math.pi - 90.0
    maxX = bbox[2] / originShift * 180.0
    maxY = math.atan(math.exp(bbox[3] / originShift * math.pi)) * 360.0 / math.pi - 90.0
    return [minX, minY, maxX, maxY]

# GDALのWARPでタイル画像を生成する
def generateImage(bbox, width, height, sourceFile, srcinfo, outFile):
    """WMS画像を生成する"""
    #ソースファイルがあるか？
    if not os.path.exists(sourceFile):
        return False
    
    # ソースファイルのbboxを取得
    if srcinfo is None:
        return False
    source_bbox = srcinfo['bbox']
    pixel_width = srcinfo.get('pixel_width', 0.0)
    pixel_height = srcinfo.get('pixel_height', 0.0)
    # ソースファイルのbboxとリクエストされたbboxが重なっているか？
    if not isBboxOverlap(source_bbox, bbox, pixel_width, pixel_height):
        return False  
    # GDALを使用してWMS画像を生成
    gdal.Warp(
        outFile,
        sourceFile,
        format='PNG',
        outputBounds=bbox,
        width=width,
        height=height,
        dstSRS='EPSG:3857',
        resampleAlg='bilinear'
    )
    return True