import re, os, math, requests
from urllib.parse import urlparse, parse_qs
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from comlib import generateImage, getKeyFromFile, isBboxOverlap, getInfoFile

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

# capabilitiesファイルからLegendURLを取得する
def getLegendURL(capabilities):
    with open(capabilities, 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r'<LegendURL>.*?<OnlineResource .*?xlink:href="(.*?)".*?</LegendURL>', content, re.DOTALL)
        if match:
            return match.group(1)
    return None

# LegendURLの画像をダウンロードしてレスポンスする
def legend(legend_url):
    response = requests.get(legend_url)
    if response.status_code == 200:
        return HttpResponse(response.content, content_type='image/png')
    else:
        return HttpResponse('Failed to fetch legend image', status=500)

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
    # マッチした部分の最後が/で終わっている場合は、/を削除する
    subpath = match_path.group(1)
    if subpath.endswith('/'):
        subpath = subpath[:-1]
    capabilities = os.path.normpath(f'{settings.TILE_SOURCE_FOLDER}/{subpath}.wms.xml')
    if not os.path.exists(capabilities):
        return HttpResponse(f'WMS is not available.{subpath}', status=404)
       
    required_params = ['SERVICE', 'REQUEST', 'VERSION']
    for param in required_params:
        if request.GET.get(param) is None:
            return HttpResponse(f'Missing required parameter: {param}', status=400)

    # パラメータのバリデーション
    if request.GET['SERVICE'].upper() != 'WMS':
        return HttpResponse('Invalid service parameter. Must be WMS.', status=400)

    # パラメータのバリデーション
    req = request.GET['REQUEST'].upper()
    if req != 'GETMAP' and req != 'GETCAPABILITIES' and req != 'GETLEGENDGRAPHIC':
        return HttpResponse('Invalid request parameter. Must be GetMap, GetCapabilities, or GetLegendGraphic.', status=400)

    # Capabilitiesを返す
    if req == 'GETCAPABILITIES':
        with open(capabilities, 'r', encoding='utf-8') as f:
            res = HttpResponse(f.read(), content_type='application/xml', charset='utf-8' )
            res['Content-Disposition'] = f'inline; filename="wms.xml"'
            return res

    # LegendURLを取得して、LegendGraphicを返す
    if req == 'GETLEGENDGRAPHIC':
        legend_url = getLegendURL(capabilities)
        if legend_url is not None:
            return legend(legend_url)
        else:
            return HttpResponse('LegendURL not found in capabilities file', status=404)

    # GetMapの必須パラメータのチェック
    required_params = ['LAYERS', 'BBOX', 'WIDTH', 'HEIGHT', 'FORMAT']
    for param in required_params:
        if request.GET.get(param) is None:
            return HttpResponse(f'Missing required parameter: {param}', status=400)

    version = request.GET['VERSION'].upper()
    
    # layersは使用しない（もともと1レイヤーしかないため）けど、必須パラメータなのでチェックだけする
    # layers = request.GET['LAYERS'].split(',')

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

    # WMS画像の生成
    sourceFile = os.path.normpath(f'{settings.TILE_SOURCE_FOLDER}/{match_path.group(1)}.tif')
    if not os.path.exists(sourceFile):
        return HttpResponse(f'Source file not found: {match_path.group(1)}.tif', status=404)
    
    # APIキーの検査
    key = getKeyFromFile(sourceFile)
    if key is not None and key != '':
        req_key = request.GET.get('APIKey')
        if req_key is None:
            return HttpResponse('Unauthorized: API key required.', status=401)
        if req_key != key:
            return HttpResponse('Unauthorized: Invalid API key.', status=401)

    fname = generateCacheFileName(bbox, width, height)
    outdir = os.path.normpath(f'{settings.WMS_OUTPUT_FOLDER}/{match_path.group(1)}/')
    if not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)
    outFile = os.path.normpath(f'{settings.WMS_OUTPUT_FOLDER}/{match_path.group(1)}/{fname}')

    # 範囲判定
    info = getInfoFile(sourceFile)
    if info is None:
        return HttpResponse(f'Not Found info file: {sourceFile}', status=404)
    if not isBboxOverlap(bbox, info['mercatorBbox']):
        return HttpResponse("WMS out of bounds.", status=404)

    # ソース画像のタイムスタンプ取得
    stime = os.path.getmtime(sourceFile)

    if os.path.exists(outFile):
        # WMS画像のタイムスタンプ取得
        ttime = os.path.getmtime(outFile)
        if ttime < stime:
            generateImage(bbox, width, height, sourceFile, outFile)
    else:
        generateImage(bbox, width, height, sourceFile, outFile)
        
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
