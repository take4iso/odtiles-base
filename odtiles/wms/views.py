import re, os, math
from urllib.parse import urlparse, parse_qs
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from comlib import getGeotiffInfo, isBboxOverlap, generateImage

#有効桁を返す
def significant_figures(min_val: float, max_val: float, size: int) -> int:
    if min_val == max_val:
        return 0
    pixel_size = (max_val - min_val) / size
    sig_figs = -int(math.floor(math.log10(abs(pixel_size))))
    return sig_figs

#有効桁数を調べて、bboxの座標を有効桁数で丸める
def round_significant_figures(bbox, width, height):
    # pwの桁数を調べる
    pw_sig_figs = significant_figures(bbox[0], bbox[2], width)
    ph_sig_figs = significant_figures(bbox[1], bbox[3], height)
    # bboxの座標を有効桁数で丸める
    rounded_bbox = [
        round(bbox[0], pw_sig_figs),
        round(bbox[1], ph_sig_figs),
        round(bbox[2], pw_sig_figs),
        round(bbox[3], ph_sig_figs)
    ]
    return rounded_bbox


# キャッシュファイル名の生成
def generateCacheFileName(bbox, width, height):
    rbbox = round_significant_figures(bbox, width, height)
    return f'{rbbox[0]}_{rbbox[1]}_{rbbox[2]}_{rbbox[3]}_{width}_{height}.png'

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
    bbox = list(map(float, request.GET['BBOX'].split(',')))
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
    fname = generateCacheFileName(bbox, width, height)
    outFile = os.path.normpath(f'{settings.WMS_OUTPUT_FOLDER}/{match_path.group(1)}/{fname}')

    # ソース画像のタイムスタンプ取得
    srcinfo = getGeotiffInfo(sourceFile)

    if os.path.exists(outFile):
        # WMS画像のタイムスタンプ取得
        ttime = os.path.getmtime(outFile)
        if ttime < srcinfo['filestamp']:
            generateImage(bbox, width, height, sourceFile, srcinfo, outFile)
    else:
        generateImage(bbox, width, height, sourceFile, srcinfo, outFile)
        
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
