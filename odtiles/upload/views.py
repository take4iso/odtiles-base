
import os, re, shutil, tempfile
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


# タイル画像を返す
@csrf_exempt
def geotiff_upload(request):
    if request.method != 'POST':
        message = '[ERROR]POSTメソッド以外のアクセスは許可されていません。'
        return HttpResponse(message, status=405)
    
    apitoken = request.headers.get('token')
    if not apitoken or apitoken == '' or apitoken != settings.UPLOAD_API_TOKEN:
        message = '[ERROR]トークンが設定されていないか、無効です。'
        return HttpResponse(message, status=403)

    if request.FILES is None or 'file' not in request.FILES:
        message = '[ERROR]ファイルがアップロードされていません。'
        return HttpResponse(message, status=400)
    file = request.FILES['file']
    
    if file.name.split('.')[-1].lower() != 'tif':
        message = '[ERROR]アップロードされたファイルの識別子が.tifではありません。'
        return HttpResponse(message, status=400)
    
    # ファイルを保存する
    with tempfile.TemporaryDirectory() as tmpdir:
        # 拡張子を小文字に変換
        base_name, ext = os.path.splitext(file.name)
        file_name = base_name + ext.lower()
        # ファイルを保存する
        with open(f'{tmpdir}/{file_name}', 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # URLパターンを正規表現で解析
        pattern = r'^/upload/(.*)'
        match = re.match(pattern, request.path)

        # ファイルの移動
        os.makedirs(f'{settings.TILE_SOURCE_FOLDER}/{match.group(1)}/', exist_ok=True)
        shutil.move(f'{tmpdir}/{file_name}', f'{settings.TILE_SOURCE_FOLDER}/{match.group(1)}/{file_name}')
        
        # タイル画像のパスが存在するか確認
        return HttpResponse(f'uploaded {settings.TILE_SOURCE_FOLDER}/{match.group(1)}/{file_name}', status=200)
