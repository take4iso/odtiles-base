import os, re, json
import xml.etree.ElementTree as ET
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .capabilities import create
from comlib import getGeotiffInfo, isBboxOverlap, setKeyFile


# Capabilitiesの設定
@csrf_exempt
def setCapabilities(request):
    # URLパターンを正規表現で解析
    pattern = r'^/setCapabilities/(.*)$'
    match = re.match(pattern, request.path)
    if match is None:
        return HttpResponse('Bad Request', status=400)

    # マッチした部分の最後が/で終わっている場合は、/を削除する
    subpath = match.group(1)
    if subpath.endswith('/'):
        subpath = subpath[:-1]

    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)   
    
    apitoken = request.headers.get('token')
    if (not apitoken or apitoken == '' or apitoken != settings.UPLOAD_API_TOKEN) and settings.DEBUG == False:
        message = '[ERROR]トークンが設定されていないか、無効です。'
        return HttpResponse(message, status=403)

    # リクエストボディのチェック（JSON形式のデータを期待）
    if request.body is None:
        message = '[ERROR]リクエストボディが設定されていません。'
        return HttpResponse(message, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        message = '[ERROR]リクエストボディがJSON形式ではありません。'
        return HttpResponse(message, status=400)
            
    # ソースファイルが存在するかをチェック
    srcfile = os.path.normpath(f'{settings.TILE_SOURCE_FOLDER}/{subpath}.tif')
    if not os.path.exists(srcfile):
        message = f'[ERROR]{subpath}.tifが見つかりません。'
        return HttpResponse(message, status=400)

    # dataのメンバーがあるかをチェック
    if len(data.keys()) == 0:
        # WMSを無効にする
        if os.path.exists(f'{settings.TILE_SOURCE_FOLDER}/{subpath}.wms.xml'):
            os.remove(f'{settings.TILE_SOURCE_FOLDER}/{subpath}.wms.xml')
        # キーファイルも削除する
        setKeyFile(None, srcfile)
        return HttpResponse('WMSを無効にしました\nAPIキーを無効にしました', status=200)

    # dataにlatlon_bboxを追加する
    info = getGeotiffInfo(srcfile)
    if info is None:
        message = f'[ERROR]{subpath}.tifのフォーマットエラーです。'
        return HttpResponse(message, status=400)     
    data['lonlat_bbox'] = info['lonlat_bbox']
    data['name'] = subpath.split('/')[-1]

    #キーファイルを設定する
    apikey = data.get('apikey')
    setKeyFile(apikey, srcfile)
    
    # フォルダ作成
    os.makedirs(f'{settings.WMS_OUTPUT_FOLDER}/{subpath}/', exist_ok=True)

    # WMSを有効にする
    base_url = settings.URL + '/wms/' + subpath + '?'
    create(base_url, data, f'{settings.TILE_SOURCE_FOLDER}/{subpath}.wms.xml')
    
    if apikey is not None and apikey != '':
        message = f'WMSを有効にしました\n{base_url}SERVICE=wms&REQUEST=GetCapabilities&VERSION=1.1.1\nAPIキーを設定しました'
    else:
        message = f'WMSを有効にしました\n{base_url}SERVICE=wms&REQUEST=GetCapabilities&VERSION=1.1.1\nAPIキーを無効にしました' 
    return HttpResponse(message, status=200)