import re
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from gdal2tiles import *

# タイル画像を返す
def tileimage(request):
    # URLパターンを正規表現で解析
    pattern = r'^/xyz/(.*)/([0-9]+)/([0-9]+)/([0-9]+)\.png$'
    match = re.match(pattern, request.path)
    if not match:
        return HttpResponse("Invalid tile request", status=400)
    if match.group(1) is None or match.group(1) == '':
        return HttpResponse("Invalid tile request", status=400)
    
    sourcefile = settings.TILE_SOURCE_FOLDER + '/' +  match.group(1) + '.tif'
    zoom = int(match.group(2))
    x = int(match.group(3))
    y = int(match.group(4))
    tilefile = f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}/{zoom}/{x}/{y}.png"

    if not os.path.exists(sourcefile):
        return HttpResponse("Not Found", status=404)
    stime = os.path.getmtime(sourcefile)

    if not os.path.exists(tilefile):
        create_ondemand_tiles(sourcefile, f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}", zoom, x, y)
    else:
        ttime = os.path.getmtime(tilefile)
        if ttime < stime:
            create_ondemand_tiles(sourcefile, f"{settings.TILE_OUTPUT_FOLDER}/{match.group(1)}", zoom, x, y)
    
    if os.path.exists(tilefile):
        max_age = settings.TILE_MAX_AGE
        if re.search(settings.TILE_LIVE_URL_PATTERN, tilefile):
            max_age = settings.TILE_MAX_AGE_LIVE
        with open(tilefile, 'rb') as f:
            res = HttpResponse(f.read(), content_type='image/png')
            res['Cache-Control'] = f'max-age={max_age}'
            return res

    return HttpResponse("Not Found", status=404)