import re, os
from urllib.parse import urlparse, parse_qs
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from osgeo import gdal

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

# WMS画像を生成する
def generate_wms_image(bbox, width, height, sourceFile, outFile):
    """WMS画像を生成する"""
    #ソースファイルがあるか？
    if not os.path.exists(sourceFile):
        return False
    
    # ソースファイルのbboxを取得
    source_bbox = get_bbox(sourceFile)
    if source_bbox is None:
        return False
    # ソースファイルのbboxとリクエストされたbboxが重なっているか？
    if not is_bbox_overlap(source_bbox, bbox):
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


# WMSの応答
def wms(request):
    if request.method != 'GET':
        return HttpResponse('Method not allowed', status=405)

    # URLパターンを正規表現で解析
    match_path = re.match(r'^/wms/(.*)', request.path)
    if match_path is None:
        return HttpResponse('Bad Request', status=400)

    # Capabilitiesファイルがなければ、WMSを止める
    capabilities = f'{settings.TILE_SOURCE_FOLDER}/{match_path.group(1)}/.wms/capabilities.xml'
    if not os.path.exists(capabilities):
        return HttpResponse('WMS is not available.', status=404)
       
    required_params = ['SERVICE', 'REQUEST', 'VERSION']
    for param in required_params:
        if request.GET.get(param) is None:
            return HttpResponse(f'Missing required parameter: {param}', status=400)

    # パラメータのバリデーション
    if request.GET['SERVICE'].upper() != 'WMS':
        return HttpResponse('Invalid service parameter. Must be WMS.', status=400)

    # パラメータのバリデーション
    if request.GET['REQUEST'].upper() != 'GETMAP' and request.GET['REQUEST'].upper() != 'GETCAPABILITIES':
        return HttpResponse('Invalid request parameter. Must be GetMap or GetCapabilities.', status=400)

    # Capabilitiesを返す
    if request.GET['REQUEST'].upper() == 'GETCAPABILITIES':
        with open(capabilities, 'r', encoding='utf-8') as f:
            res = HttpResponse(f.read(), content_type='application/xml', charset='utf-8' )
            res['Content-Disposition'] = f'inline; filename="capabilities.xml"'
            return res


    # GetMapの必須パラメータのチェック
    required_params = ['LAYERS', 'BBOX', 'WIDTH', 'HEIGHT', 'FORMAT']
    for param in required_params:
        if request.GET.get(param) is None:
            return HttpResponse(f'Missing required parameter: {param}', status=400)

    version = request.GET['VERSION'].upper()
    layers = request.GET['LAYERS'].split(',')
    if 'CRS' in request.GET:
        crs = str(request.GET['CRS']).upper()
    if 'SRS' in request.GET:
        crs = str(request.GET['SRS']).upper()
    bbox = request.GET['BBOX'].split(',')
    width = int(request.GET['WIDTH'])
    height = int(request.GET['HEIGHT'])
    format = request.GET['FORMAT'].upper()

    if not(version == '1.1.1' or version == '1.3.0'):
        return HttpResponse('Invalid version parameter. Must be 1.1.1 or 1.3.0.', status=400)

    if crs != 'EPSG:3857':
        return HttpResponse('Invalid CRS/SRS parameter. Must be EPSG:3857.', status=400)

    if width <= 0 or height <= 0:
        return HttpResponse('Invalid width or height parameter. Must be positive integers.', status=400)

    if format != 'IMAGE/PNG':
        return HttpResponse('Invalid format parameter. Must be image/png.', status=400)

    if len(layers) == 0:
        return HttpResponse('Invalid layers parameter. At least one layer must be specified.', status=400)
    if len(layers) > 1:
        return HttpResponse('Invalid layers parameter. Only one layer is supported per request.', status=400)

    # WMS画像の生成
    sourceFile = os.path.normpath(f'{settings.TILE_SOURCE_FOLDER}/{match_path.group(1)}/{layers[0]}.tif')
    outFile = os.path.normpath(f'{settings.WMS_OUTPUT_FOLDER}/{match_path.group(1)}/{bbox[0]}.{bbox[1]}.{bbox[2]}.{bbox[3]}.{width}.{height}.png')

    # ソース画像のタイムスタンプ取得
    stime = os.path.getmtime(sourceFile)

    if os.path.exists(outFile):
        # WMS画像のタイムスタンプ取得
        ttime = os.path.getmtime(outFile)
        if ttime < stime:
            generate_wms_image(bbox, width, height, sourceFile, outFile)
    else:
        generate_wms_image(bbox, width, height, sourceFile, outFile)
        
    if os.path.exists(outFile):
        # ブラウザキャッシュの期間を設定
        max_age = settings.MAX_AGE
        if re.search(settings.LIVE_URL_PATTERN, outFile):
            max_age = settings.MAX_AGE_LIVE
        with open(outFile, 'rb') as f:
            res = HttpResponse(f.read(), content_type='image/png')
            res['Cache-Control'] = f'max-age={max_age}'
            return res       
    else:
        return HttpResponse('Not Found.', status=404)
