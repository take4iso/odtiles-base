import os, re, math
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from osgeo import gdal

originShift = 20037508.342789244

# GeoTIFFの範囲（bbox）を取得する
def get_bbox(sourceFile):
    """GeoTIFFの範囲（bbox）を取得する"""
    if not os.path.exists(sourceFile):
        return None
    ds = gdal.Open(sourceFile)
    gt = ds.GetGeoTransform()
    x_min = gt[0]
    y_max = gt[3]
    x_max = x_min + gt[1] * ds.RasterXSize
    y_min = y_max + gt[5] * ds.RasterYSize
    return [x_min, y_min, x_max, y_max]

# 2つのbboxが重なっているかを判定する
def is_bbox_overlap(bbox1, bbox2):
    """2つのbboxが重なっているかを判定する"""
    if bbox1[0] >= bbox2[2] or bbox1[2] <= bbox2[0] or bbox1[1] >= bbox2[3] or bbox1[3] <= bbox2[1]:
        return False
    return True

# XYZからメルカトル座標のBBOXを計算する
def xyz_to_mercator_bbox(x, y, z):
    initialResolution = 2 * originShift / 256
    resolution = initialResolution / (2 ** z)

    minX = x * 256 * resolution - originShift
    maxY = originShift - y * 256 * resolution
    maxX = (x + 1) * 256 * resolution - originShift
    minY = originShift - (y + 1) * 256 * resolution

    return (minX, minY, maxX, maxY)

# GDALのWARPでタイル画像を生成する
def create_ondemand_tiles(sourcefile, outputpath, zoom, x, y):
    # XYZからメルカトル座標のBBOXを計算
    bbox = xyz_to_mercator_bbox(x, y, zoom)
    # ソースファイルのbboxを取得
    source_bbox = get_bbox(sourcefile)
    if source_bbox is None:
        return False
    # ソースファイルのbboxとリクエストされたbboxが重なっているか？
    if not is_bbox_overlap(source_bbox, bbox):
        return False
    outputfile = f"{outputpath}/{zoom}/{x}/{y}.png"
    os.makedirs(f'{outputpath}/{zoom}/{x}/', exist_ok=True)
    gdal.Warp(
        outputfile,
        sourcefile,
        format='PNG',
        outputBounds=bbox,
        width=256,
        height=256,
        dstSRS='EPSG:3857',
        resampleAlg='bilinear'
    )
    return True

# タイル画像を返す
def tileimage(request):
    if request.method != 'GET':
        return HttpResponse('Method not allowed', status=405)
    # URLパターンを正規表現で解析
    pattern = r'^/xyz/(.*)/([0-9]+)/([0-9]+)/([0-9]+)\.png$'
    match = re.match(pattern, request.path)
    if not match:
        return HttpResponse("Invalid tile request", status=400)
    if match.group(1) is None or match.group(1) == '':
        return HttpResponse("Invalid tile request", status=400)
    
    sourcefile = os.path.normpath(settings.TILE_SOURCE_FOLDER + '/' +  match.group(1) + '.tif')
    zoom = int(match.group(2))
    x = int(match.group(3))
    y = int(match.group(4))
    tilefile = os.path.normpath(f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}/{zoom}/{x}/{y}.png")

    if not os.path.exists(sourcefile):
        return HttpResponse("Not Found", status=404)
    
    # ソース画像のタイムスタンプ取得
    stime = os.path.getmtime(sourcefile)

    if not os.path.exists(tilefile):
        create_ondemand_tiles(sourcefile, os.path.normpath(f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}"), zoom, x, y)
    else:
        # タイル画像のタイムスタンプ取得
        ttime = os.path.getmtime(tilefile)
        if ttime < stime:
            create_ondemand_tiles(sourcefile, os.path.normpath(f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}"), zoom, x, y)
    
    if os.path.exists(tilefile):
        # ブラウザキャッシュの期間を設定
        max_age = settings.MAX_AGE
        if re.search(settings.LIVE_URL_PATTERN, tilefile):
            max_age = settings.MAX_AGE_LIVE
        with open(tilefile, 'rb') as f:
            res = HttpResponse(f.read(), content_type='image/png')
            res['Cache-Control'] = f'max-age={max_age}'
            return res

    return HttpResponse("Not Found", status=404)