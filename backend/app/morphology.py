"""Y轴竖直的网格截面测量，统一展示高度30。"""
import numpy as np
import trimesh
from scipy.spatial import ConvexHull, QhullError

DISPLAY_HEIGHT = 30.0


def result(height, diameter, mouth, foot, position, shape, source):
    if min(height, diameter, mouth, foot) <= 0:
        raise ValueError('高度、腹径、口径与足径必须大于零')
    scale = DISPLAY_HEIGHT / height
    return dict(height=DISPLAY_HEIGHT, maxBellyDiameter=float(diameter*scale),
                mouthDiameter=float(mouth*scale), footDiameter=float(foot*scale),
                heightBellyRatio=float(height/diameter), bellyPosition=float(position),
                bellyPositionLabel='偏下' if position < .4 else '偏上' if position > .6 else '居中',
                shape=[[float(r*scale), float(y*scale)] for r,y in shape],
                source=source, method='自动提取', unit='归一化单位（高度=30）')


def measure_profile(profile):
    points = np.array(profile, dtype=float, copy=True)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2:
        raise ValueError('轮廓至少需要两个 [半径, 高度] 点')
    if not np.isfinite(points).all() or (points[:,0] < 0).any():
        raise ValueError('轮廓坐标必须有限，半径不得小于零')
    points = points[np.argsort(points[:,1])]
    if (np.diff(points[:,1]) <= 0).any():
        raise ValueError('轮廓高度必须互不重复')
    points[:,1] -= points[0,1]
    height = points[-1,1]
    widest = np.flatnonzero(np.isclose(points[:,0],points[:,0].max()))
    position = float(np.mean(points[widest,1])/height)
    return result(height,points[:,0].max()*2,points[-1,0]*2,points[0,0]*2,position,points,'profile')


def diameter_of(points):
    points = np.unique(points[:,[0,2]],axis=0)
    if len(points) < 2: return 0.
    if len(points) > 2:
        try: points = points[ConvexHull(points).vertices]
        except QhullError: return float(np.linalg.norm(points.max(axis=0)-points.min(axis=0)))
    if len(points)==2: return float(np.linalg.norm(points[0]-points[1]))
    # 旋转卡尺计算凸包直径，避免大型截面的成对距离矩阵。
    j,best=1,0.
    def distance(a,b): return float(np.sum((a-b)**2))
    def area(edge,point): return abs(float(edge[0]*point[1]-edge[1]*point[0]))
    for i in range(len(points)):
        nxt=(i+1)%len(points);edge=points[nxt]-points[i]
        for _ in range(len(points)):
            nj=(j+1)%len(points)
            if area(edge,points[nj]-points[i]) <= area(edge,points[j]-points[i])+1e-10: break
            j=nj
        best=max(best,distance(points[i],points[j]),distance(points[nxt],points[j]))
        nj=(j+1)%len(points)
        if abs(area(edge,points[nj]-points[i])-area(edge,points[j]-points[i]))<1e-10:
            best=max(best,distance(points[i],points[nj]))
    return best**.5


def measure_mesh(mesh):
    if not isinstance(mesh,trimesh.Trimesh) or not len(mesh.faces):
        raise ValueError('文件没有三角网格')
    if len(mesh.faces) > 300_000:
        raise ValueError('模型超过30万面，请先简化网格')
    if not np.isfinite(mesh.vertices).all(): raise ValueError('网格包含无效坐标')
    low, high = mesh.bounds[:,1]
    height = high-low
    if height <= 1e-9: raise ValueError('Y轴高度为零，请检查竖直轴')
    samples = []
    for fraction in np.linspace(.005,.995,101):
        lines = trimesh.intersections.mesh_plane(mesh,[0,1,0],[0,low+fraction*height,0])
        if len(lines):
            diameter = diameter_of(lines.reshape(-1,3))
            if diameter > 0: samples.append((float(fraction),diameter))
    if len(samples) < 5: raise ValueError('有效截面不足，无法提取器型参数')
    fractions, diameters = np.array(samples).T
    bottom, top = diameters[fractions <= .03], diameters[fractions >= .97]
    if not len(bottom) or not len(top): raise ValueError('器口或器足截面缺失')
    maximum = diameters.max()
    position = float(np.mean(fractions[np.isclose(diameters,maximum,rtol=.001)]))
    mouth, foot = float(np.median(top)), float(np.median(bottom))
    shape = [(foot/2,0),*[(float(d/2),float(f*height)) for f,d in samples],(mouth/2,height)]
    return result(height,maximum,mouth,foot,position,shape,'mesh')


def normalize_mesh(mesh, up_axis='y'):
    directions={'y':[0,1,0],'-y':[0,-1,0],'z':[0,0,1],'-z':[0,0,-1],'x':[1,0,0],'-x':[-1,0,0]}
    if up_axis not in directions: raise ValueError('竖直轴无效')
    mesh = mesh.copy()
    mesh.apply_transform(trimesh.geometry.align_vectors(directions[up_axis],[0,1,0]))
    low,high=mesh.bounds
    height=high[1]-low[1]
    if height <= 1e-9: raise ValueError('模型高度为零')
    mesh.apply_translation([-float((low[0]+high[0])/2),-float(low[1]),-float((low[2]+high[2])/2)])
    mesh.apply_scale(DISPLAY_HEIGHT/height)
    return mesh


def compare_measurements(left,right,left_label,right_label):
    rows=[dict(label=label,left=f'{left[key]:.2f}',right=f'{right[key]:.2f}')
          for label,key in [('高度（归一化）','height'),('最大腹径','maxBellyDiameter'),
                           ('口径（外径）','mouthDiameter'),('足径（外径）','footDiameter'),('高 / 腹径','heightBellyRatio')]]
    rows.append(dict(label='最大腹径位置（距底部）',left=f"{left['bellyPosition']:.1%} · {left['bellyPositionLabel']}",
                     right=f"{right['bellyPosition']:.1%} · {right['bellyPositionLabel']}"))
    ratio=left['heightBellyRatio']-right['heightBellyRatio']
    form='比例相近' if abs(ratio)<.03 else '更修长' if ratio>0 else '更敦实'
    insight=f'统一高度后，{left_label}相较于{right_label}{form}。'
    for key,title in [('mouthDiameter','口径'),('footDiameter','足径')]:
        delta=(left[key]/right[key]-1)*100
        insight+=f"{title}{'大' if delta>=0 else '小'}约{abs(delta):.1f}%。"
    shift=(left['bellyPosition']-right['bellyPosition'])*100
    insight+=f"最大腹径位置{'高' if shift>=0 else '低'}{abs(shift):.1f}个高度百分点。"
    return dict(rows=rows,insight=insight,leftLabel=left_label,rightLabel=right_label,
                leftMeasurement=left,rightMeasurement=right)
