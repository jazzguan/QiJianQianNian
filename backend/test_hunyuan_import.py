# -*- coding: utf-8 -*-
import sys

ROOT = r"D:\软创赛\QiJianQianNian\backend\cache\Hunyuan3D-2-main"
sys.path.insert(0, ROOT)

from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline  # noqa
from hy3dgen.rembg import BackgroundRemover  # noqa

print("形状管线导入 OK")
print("Pipeline:", Hunyuan3DDiTFlowMatchingPipeline.__name__)
