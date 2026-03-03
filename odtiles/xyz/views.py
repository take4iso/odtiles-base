import os, re, math
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from comlib import xyzToMercatorBbox, generateImage, getGeotiffInfo, isBboxOverlap




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

    outdir = os.path.normpath(f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}/{zoom}/{x}")
    outfile = os.path.normpath(f"{outdir}/{y}.png")

    if not os.path.exists(sourcefile):
        return HttpResponse("Not Found", status=404)
    
    # ソース画像のタイムスタンプ取得
    stime = os.path.getmtime(sourcefile)
    srcinfo = getGeotiffInfo(sourcefile)
    tgbbox = xyzToMercatorBbox(x, y, zoom)

    if not os.path.exists(outfile):
        if isBboxOverlap(srcinfo['bbox'], tgbbox, srcinfo.get('pixel_width', 0.0), srcinfo.get('pixel_height', 0.0)):
            os.makedirs(outdir, exist_ok=True)
            generateImage(tgbbox, 256, 256, sourcefile, srcinfo, outfile)
    else:
        # タイル画像のタイムスタンプ取得
        ttime = os.path.getmtime(outfile)
        if ttime < stime:
            generateImage(tgbbox, 256, 256, sourcefile, srcinfo, outfile)
    
    if os.path.exists(outfile):
        # ブラウザキャッシュの期間を設定
        max_age = settings.MAX_AGE
        if re.search(settings.LIVE_URL_PATTERN, outfile):
            max_age = settings.MAX_AGE_LIVE
        with open(outfile, 'rb') as f:
            res = HttpResponse(f.read(), content_type='image/png')
            res['Cache-Control'] = f'max-age={max_age}'
            return res

    return HttpResponse("Not Found", status=404)