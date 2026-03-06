
import os, re, shutil, tempfile, json
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# GeoTIFFのアップロード
@csrf_exempt
def geotiff_upload(request):
    if request.method != 'POST':
        message = '[ERROR]POSTメソッド以外のアクセスは許可されていません。'
        return HttpResponse(message, status=405)
    
    apitoken = request.headers.get('token')
    if (not apitoken or apitoken == '' or apitoken != settings.UPLOAD_API_TOKEN) and settings.DEBUG == False:
        message = '[ERROR]トークンが設定されていないか、無効です。'
        return HttpResponse(message, status=403)

    if request.FILES is None or 'file' not in request.FILES:
        message = '[ERROR]ファイルがアップロードされていません。'
        return HttpResponse(message, status=400)
    file = request.FILES['file']
    
    if file.name.split('.')[-1].lower() != 'tif':
        message = '[ERROR]アップロードされたファイルの識別子が.tifではありません。'
        return HttpResponse(message, status=400)
    
    # URLパターンを正規表現で解析
    pattern = r'^/upload/(.*)/+$'
    match = re.match(pattern, request.path)
    datadir = os.path.normpath(f'{settings.TILE_SOURCE_FOLDER}/{match.group(1)}/')
    # データディレクトリを作成
    os.makedirs(datadir, exist_ok=True)
    # 拡張子を小文字に変換
    base_name, ext = os.path.splitext(file.name)
    file_name = base_name + ext.lower()
    # データファイルと凡例ファイルのパスを生成
    datafile = os.path.normpath(f'{datadir}/{file_name}')

    # POSTリクエストのファイルを保存する
    with tempfile.TemporaryDirectory() as tmpdir:
        # ファイルを保存する
        with open(f'{tmpdir}/{file_name}', 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # ファイルの移動
        shutil.move(os.path.normpath(f'{tmpdir}/{file_name}'), datafile)
        
        # タイル画像のパスが存在するか確認
        return HttpResponse(f'uploaded {datafile}', status=200)
    
    return HttpResponse('Unknown error', status=500)