from django.test import TestCase
from django.conf import settings
from comlib import getLonlatBbox, xyzToMercatorBbox
# Create your tests here.

def test_get_bbox():
    testdata = settings.BASE_DIR / 'debugdata/testdata.tif'
    bbox = getLonlatBbox(testdata)
    # 浮動小数点の精度を考慮した比較
    assert abs(bbox[0] - 120.5) < 1e-10
    assert abs(bbox[1] - 21.0) < 1e-10
    assert abs(bbox[2] - 149.0) < 1e-10
    assert abs(bbox[3] - 46.666666666666667) < 1e-10

def test_xyz_to_mercator_bbox1():
    bbox = xyzToMercatorBbox(0, 0, 0)
    assert bbox == [-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244]

def test_xyz_to_mercator_bbox2():
    bbox = xyzToMercatorBbox(6, 57, 27)
    print(bbox)
    assert bbox == [-20037506.551296394, 20037491.02502502, -20037506.25271425, 20037491.323607165]
