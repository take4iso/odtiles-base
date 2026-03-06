import os, re, math
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from comlib import xyzToMercatorBbox, generateImage, getKeyFromFile, getInfoFile, isBboxOverlap




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
    if not os.path.exists(sourcefile):
        return HttpResponse("Not Found source file.", status=404)
    info = getInfoFile(sourcefile)
    if info is None:
        return HttpResponse("Not Found info file.", status=404)

    zoom = int(match.group(2))
    x = int(match.group(3))
    y = int(match.group(4))

    outdir = os.path.normpath(f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}/{zoom}/{x}")
    outfile = os.path.normpath(f"{outdir}/{y}.png")

    
    # APIキーの検査
    key = getKeyFromFile(sourcefile)
    if key is not None and key != '':
        req_key = request.GET.get('APIKey')
        if req_key is None:
            return HttpResponse('Unauthorized: API key required.', status=401)
        if req_key != key:
            return HttpResponse('Unauthorized: Invalid API key.', status=401)

    # ソース画像のタイムスタンプ取得
    stime = os.path.getmtime(sourcefile)
    tgbbox = xyzToMercatorBbox(x, y, zoom)

    # タイルのBBOXとGeoTIFFのBBOXが重なっているかを確認する
    if not isBboxOverlap(tgbbox, info['mercatorBbox']):
        return HttpResponse("Tile out of bounds.", status=404)

    if not os.path.exists(outfile):
        os.makedirs(outdir, exist_ok=True)
        generateImage(tgbbox, 256, 256, sourcefile, outfile)
    else:
        # タイル画像のタイムスタンプ取得
        ttime = os.path.getmtime(outfile)
        if ttime < stime:
            generateImage(tgbbox, 256, 256, sourcefile, outfile)
    

    if os.path.exists(outfile):
        # ブラウザキャッシュの期間を設定
        max_age = settings.MAX_AGE
        if re.search(settings.LIVE_URL_PATTERN, outfile):
            max_age = settings.MAX_AGE_LIVE
        with open(outfile, 'rb') as f:
            res = HttpResponse(f.read(), content_type='image/png')
            res['Cache-Control'] = f'max-age={max_age}'
            return res

    return HttpResponse("Not Found.", status=404)