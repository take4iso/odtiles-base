import os, re, json
import xml.etree.ElementTree as ET
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .capabilities import create

# Capabilitiesの設定
@csrf_exempt
def setCapabilities(request):
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
        print(request.body)
        message = '[ERROR]リクエストボディがJSON形式ではありません。'
        return HttpResponse(message, status=400)

    # URLパターンを正規表現で解析
    pattern = r'^/setCapabilities/(.*)'
    match = re.match(pattern, request.path)

    if data.get('layers') is None:
        # layersがない場合は、WMSを無効にする
        if os.path.exists(f'{settings.TILE_SOURCE_FOLDER}/{match.group(1)}/.wms/capabilities.xml'):
            os.remove(f'{settings.TILE_SOURCE_FOLDER}/{match.group(1)}/.wms/capabilities.xml')
        return HttpResponse('WMSを無効にしました', status=200)
        
    # フォルダ作成
    os.makedirs(f'{settings.TILE_SOURCE_FOLDER}/{match.group(1)}/.wms', exist_ok=True)
    os.makedirs(f'{settings.WMS_OUTPUT_FOLDER}/{match.group(1)}/', exist_ok=True)

    # Capabilitiesの生成
    base_url = settings.URL + '/wms/' + match.group(1)
    create(base_url, data['layers'], f'{settings.TILE_SOURCE_FOLDER}/{match.group(1)}/.wms/capabilities.xml')

    return HttpResponse(f'WMSを有効にしました\n{base_url}?SERVICE=wms&REQUEST=GetCapabilities&VERSION=1.1.1', status=200)