import os
import xml.etree.ElementTree as ET

# 名前空間の登録 (ns0:href になるのを防ぐ)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

def getXmlRoot():
    """template.xmlをパースしてtreeとroot要素を返す"""
    # capabilities.py と同じディレクトリにある template.xml を指す
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, 'template.xml')
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at: {template_path}")
        
    tree = ET.parse(template_path)
    return tree, tree.getroot()

def updateCapabilities(base_url="http://localhost:8000/wms", data=None):
    """XMLの内容を動的に更新・追加する例"""
    tree, root = getXmlRoot()

    # すべての OnlineResource の URL を更新
    xlink_href = '{http://www.w3.org/1999/xlink}href'
    for onlineResource in root.findall('.//OnlineResource'):
        onlineResource.attrib[xlink_href] = base_url

    # Service タグの Title を更新
    service_title = root.find('.//Service/Title')
    if service_title is not None and data is not None and data.get('title') is not None:
        service_title.text = data['title']
    # 新しいレイヤーの追加 (ユーザーのリクエスト)
    # 親となる Layer 要素を取得
    parent_layer = root.find('.//Capability//Layer')
    if parent_layer is not None:
        new_layer = ET.SubElement(parent_layer, 'Layer')
        
        # サブエレメントを追加
        if data.get('name') is not None :
            ET.SubElement(new_layer, 'Name').text = str(data['name'])
        if data.get('title') is not None:
            ET.SubElement(new_layer, 'Title').text = str(data['title'])
        ET.SubElement(new_layer, 'SRS').text = 'EPSG:3857'
        
        if data.get('latlonBbox') is not None:
            latlon_bbox = data['latlonBbox']
            ET.SubElement(new_layer, 'LatLonBoundingBox', {
                'minx': str(latlon_bbox[0]), 'miny': str(latlon_bbox[1]), 
                'maxx': str(latlon_bbox[2]), 'maxy': str(latlon_bbox[3])
            })
        else:
            # 属性を持つサブエレメントを追加
            ET.SubElement(new_layer, 'LatLonBoundingBox', {
                'minx': '-180', 'miny': '-90', 'maxx': '180', 'maxy': '90'
            })

        #スタイルサブエレメント
        if data.get('legendUrl') is not None:
            style = ET.SubElement(new_layer, 'Style')
            legendUrl = ET.SubElement(style, 'LegendURL')
            ET.SubElement(legendUrl, 'Format').text = 'image/png'
            ET.SubElement(legendUrl, 'OnlineResource', {
                'xlink:type':'simple', xlink_href: f'{data["legendUrl"]}'
            })

    # インデントを付ける
    ET.indent(tree, space="  ", level=0)
    return tree

# xmlを保存する
def saveXml(tree, filepath):
    tree.write(filepath, encoding='utf-8', xml_declaration=True)



# Capabilitiesの生成
def create(baseurl:str, data:dict, filepath:str):
    tree = updateCapabilities(baseurl, data)
    saveXml(tree, filepath)


# デバック実行用
"""
if __name__ == "__main__":
    try:
        tree = updateCapabilities("https://example.com/wms",[{"file":"testdata.tif","title":"ナウキャスト"}])
        saveXml(tree, "test.xml")
    except Exception as e:
        print(f"Error: {e}")
"""