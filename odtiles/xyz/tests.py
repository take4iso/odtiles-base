from django.test import TestCase
from django.conf import settings
from .views import get_bbox, is_bbox_overlap, xyz_to_mercator_bbox, create_ondemand_tiles
# Create your tests here.

def test_get_bbox():
    testdata = settings.BASE_DIR / 'debugdata/testdata.tif'
    bbox = get_bbox(testdata)
    assert bbox == [120.5, 21.000000000000224, 148.99999999997408, 46.66666666666667]

def test_xyz_to_mercator_bbox1():
    bbox = xyz_to_mercator_bbox(0, 0, 0)
    assert bbox == [-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244]

def test_xyz_to_mercator_bbox2():
    bbox = xyz_to_mercator_bbox(6, 57, 27)
    print(bbox)
    assert bbox == [-20037506.551296394, 20037491.02502502, -20037506.25271425, 20037491.323607165]

def test_is_bbox_overlap():
    assert is_bbox_overlap([0, 0, 10, 10], [5, 5, 15, 15]) == True
    assert is_bbox_overlap([0, 0, 10, 10], [10, 10, 20, 20]) == False
    assert is_bbox_overlap([0, 0, 10, 10], [-5, -5, 5, 5]) == True
    assert is_bbox_overlap([0, 0, 10, 10], [-5, -5, -1, -1]) == False