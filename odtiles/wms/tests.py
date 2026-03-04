from django.test import TestCase
from .views import  significant_figures, round_significant_figures

def test_significant_figures():
    # pixel_size = (max - min) / size
    # sig_figs = -floor(log10(pixel_size))
    assert significant_figures(0, 10, 100) == 1        # pixel_size=0.1, log10(0.1)=-1, -(-1)=1
    assert significant_figures(0, 1, 100) == 2         # pixel_size=0.01, log10(0.01)=-2, -(-2)=2
    assert significant_figures(0, 0.01, 100) == 4      # pixel_size=0.0001, log10(0.0001)=-4, -(-4)=4
    assert significant_figures(0, 0.0001, 100) == 6    # pixel_size=0.000001, log10(0.000001)=-6, -(-6)=6
    assert significant_figures(0, 0.000001, 100) == 8  # pixel_size=0.00000001, log10=-8, -(-8)=8
    assert significant_figures(13413998.64058946259, 16586604.12819487788, 82) == -4

def test_round_significant_figures():
    bbox = [13413998.64058946259, 2391878.587944341823, 16586604.12819487788, 5887834.302669902332]
    width = 82
    height = 91
    rounded_bbox = round_significant_figures(bbox, width, height)
    # 実際の有効桁数で丸めた結果
    assert rounded_bbox == [13410000.0, 2390000.0, 16590000.0, 5890000.0]
