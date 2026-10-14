import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import type { MutableRefObject, ReactNode } from 'react'
import * as THREE from 'three'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { ContactShadows, Html, OrbitControls, useGLTF } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { createGlazeTexture } from './textures'
import type { GlazeStyle, PorcelainPart, PorcelainShape } from '../../types/porcelain'

export interface SyncState {
  position: [number, number, number]
  target: [number, number, number]
  from: string
  anchorY?: number
}

export interface PorcelainViewerProps {
  /** 未来后端返回的 GLB 地址，优先于 shape 使用；加载失败时回退到程序化轮廓 */
  modelUrl?: string
  /** 不确定性热力图 GLB 地址（与 modelUrl 同坐标系，用于切换显示） */
  heatmapUrl?: string
  /** true 显示热力图，false 显示原始纹理 */
  showHeatmap?: boolean
  shape?: PorcelainShape
  glaze?: GlazeStyle
  autoRotate?: boolean
  interactive?: boolean
  showControls?: boolean
  /** 部位标注数据（用于点击交互与选中高亮） */
  parts?: PorcelainPart[]
  /** 当前选中的部位 id，查看器据此高亮对应区域 */
  selectedPartId?: string
  /** 用户点击某部位后的回调 */
  onPartSelect?: (partId: string) => void
  className?: string
  /** 外部触发重置（值变化即重置视角） */
  resetToken?: number
  /** 双模型同步交互 */
  viewId?: string
  syncEnabled?: boolean
  syncRef?: MutableRefObject<SyncState | null>
  framingRadius?: number
  focusRegion?: { yMin: number; yMax: number }
  normalizeModel?: boolean
}

const DEFAULT_SHAPE: PorcelainShape = [
  [3.5, 0],
  [4, 1],
  [4.5, 2.5],
  [6.5, 6],
  [8.6, 11],
  [9.1, 16],
  [7.5, 21],
  [5, 25],
  [3, 28],
  [2.6, 29.5],
  [3.8, 31],
]

const DEFAULT_GLAZE: GlazeStyle = {
  color: '#86a6a6',
  roughness: 0.38,
  metalness: 0.05,
  clearcoat: 0.5,
  decoration: 'celadon',
}

const _v1 = new THREE.Vector3()
const _v2 = new THREE.Vector3()

function computeBounds(shape: PorcelainShape): { minY: number; maxY: number; maxR: number } {
  let minY = Infinity
  let maxY = -Infinity
  let maxR = 0
  for (const [x, y] of shape) {
    if (y < minY) minY = y
    if (y > maxY) maxY = y
    if (x > maxR) maxR = x
  }
  return { minY, maxY, maxR }
}

function radiusAt(shape: PorcelainShape, y: number): number {
  const sorted = [...shape].sort((a, b) => a[1] - b[1])
  if (y <= sorted[0][1]) return sorted[0][0]
  if (y >= sorted[sorted.length - 1][1]) return sorted[sorted.length - 1][0]
  for (let i = 0; i < sorted.length - 1; i++) {
    const [x0, y0] = sorted[i]
    const [x1, y1] = sorted[i + 1]
    if (y >= y0 && y <= y1) {
      const t = (y - y0) / (y1 - y0 || 1)
      return x0 + (x1 - x0) * t
    }
  }
  return 0
}

function segmentProfile(shape: PorcelainShape, yMin: number, yMax: number): PorcelainShape {
  const sorted = [...shape].sort((a, b) => a[1] - b[1])
  const pts: PorcelainShape = [[radiusAt(shape, yMin) * 1.015, yMin]]
  for (const [x, y] of sorted) {
    if (y > yMin && y < yMax) pts.push([x * 1.015, y])
  }
  pts.push([radiusAt(shape, yMax) * 1.015, yMax])
  return pts
}

function findPart(parts: PorcelainPart[] | undefined, y: number): PorcelainPart | undefined {
  if (!parts) return undefined
  for (const p of parts) {
    if (y >= p.yMin && y <= p.yMax) return p
  }
  return undefined
}

function Vessel({
  shape,
  glaze,
  highlightRegion,
  parts,
  onPartSelect,
}: {
  shape: PorcelainShape
  glaze: GlazeStyle
  highlightRegion?: { yMin: number; yMax: number }
  parts?: PorcelainPart[]
  onPartSelect?: (partId: string) => void
}) {
  const geometry = useMemo(() => {
    const points = shape.map(([x, y]) => new THREE.Vector2(x, y))
    return new THREE.LatheGeometry(points, 96)
  }, [shape])

  const texture = useMemo(() => createGlazeTexture(glaze.decoration), [glaze.decoration])

  const meshRef = useRef<THREE.Mesh>(null)

  const handleClick = (e: { point: THREE.Vector3 }) => {
    if (!onPartSelect || !meshRef.current) return
    const local = meshRef.current.worldToLocal(e.point.clone())
    const part = findPart(parts, local.y)
    if (part) onPartSelect(part.id)
  }

  return (
    <group>
      <mesh ref={meshRef} geometry={geometry} onClick={handleClick} castShadow>
        <meshPhysicalMaterial
          map={texture}
          color={glaze.color}
          roughness={glaze.roughness}
          metalness={glaze.metalness}
          clearcoat={glaze.clearcoat}
          clearcoatRoughness={0.25}
        />
      </mesh>
      {highlightRegion && <HighlightSegment shape={shape} region={highlightRegion} />}
    </group>
  )
}

function HighlightSegment({ shape, region }: { shape: PorcelainShape; region: { yMin: number; yMax: number } }) {
  const geometry = useMemo(() => {
    const points = segmentProfile(shape, region.yMin, region.yMax).map(([x, y]) => new THREE.Vector2(x, y))
    return new THREE.LatheGeometry(points, 96)
  }, [shape, region])

  return (
    <mesh geometry={geometry} renderOrder={2}>
      <meshBasicMaterial color="#c9a96b" transparent opacity={0.5} side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  )
}

function GLTFModel({ url, visible = true, normalize = false, region }: { url: string; visible?: boolean; normalize?: boolean; region?: { yMin: number; yMax: number } }) {
  const { scene } = useGLTF(url)
  const copy = useMemo(() => scene.clone(true), [scene])
  const box = useMemo(() => new THREE.Box3().setFromObject(copy), [copy])
  const scale = normalize ? 30 / Math.max(box.max.y - box.min.y, .001) : 1
  const center = box.getCenter(new THREE.Vector3())
  const overlay = useMemo(() => {
    if (!region) return null
    const clone = copy.clone(true)
    clone.traverse(obj => {
      if (!(obj as THREE.Mesh).isMesh) return
      const mesh = obj as THREE.Mesh
      mesh.material = new THREE.MeshBasicMaterial({ color: '#c9a96b', transparent: true, opacity: .25,
        side: THREE.DoubleSide, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1,
        clippingPlanes: [new THREE.Plane(new THREE.Vector3(0,1,0), -region.yMin), new THREE.Plane(new THREE.Vector3(0,-1,0), region.yMax)] })
    })
    return clone
  }, [copy, region?.yMin, region?.yMax])
  useEffect(() => () => { overlay?.traverse(obj => { if ((obj as THREE.Mesh).isMesh) ((obj as THREE.Mesh).material as THREE.Material).dispose() }) }, [overlay])
  return <group visible={visible} scale={scale} position={normalize ? [-center.x*scale, -box.min.y*scale, -center.z*scale] : [0,0,0]}>
    <primitive object={copy} />{overlay && <primitive object={overlay} />}
  </group>
}

function LoadingFallback() {
  return (
    <Html center>
      <div className="whitespace-nowrap text-xs text-ink-soft">模型加载中…</div>
    </Html>
  )
}

class ModelErrorBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  render() {
    return this.state.hasError ? this.props.fallback : this.props.children
  }
}

function Rig({
  bounds,
  resetToken,
  cameraDistance,
  controlsRef,
  syncEnabled,
  syncRef,
  viewId,
  focusRegion,
}: {
  bounds: { minY: number; maxY: number; maxR: number }
  resetToken: number
  cameraDistance: number
  controlsRef: MutableRefObject<OrbitControlsImpl | null>
  syncEnabled?: boolean
  syncRef?: MutableRefObject<SyncState | null>
  viewId?: string
  focusRegion?: { yMin: number; yMax: number }
}) {
  const { camera } = useThree()

  useEffect(() => {
    if (resetToken <= 0 && !focusRegion) return
    const targetY = focusRegion ? (focusRegion.yMin + focusRegion.yMax) / 2 : (bounds.maxY + bounds.minY) / 2
    camera.position.set(0, targetY, focusRegion ? Math.max(bounds.maxR*3, cameraDistance*.55) : cameraDistance)
    if (controlsRef.current) {
      controlsRef.current.target.set(0, targetY, 0)
      controlsRef.current.update()
    }
  }, [resetToken, bounds, cameraDistance, camera, controlsRef, focusRegion?.yMin, focusRegion?.yMax])

  useFrame(() => {
    if (!syncEnabled || !syncRef?.current || !controlsRef.current) return
    const s = syncRef.current
    if (s.from === viewId) return
    const anchor = focusRegion ? (focusRegion.yMin + focusRegion.yMax)/2 : (bounds.maxY + bounds.minY)/2
    const offset = anchor - (s.anchorY ?? anchor)
    camera.position.copy(_v1.set(s.position[0], s.position[1]+offset, s.position[2]))
    controlsRef.current.target.copy(_v2.set(s.target[0], s.target[1]+offset, s.target[2]))
    controlsRef.current.update()
  })

  return null
}

function ViewerControls({
  autoRotate,
  onToggleAutoRotate,
  onReset,
}: {
  autoRotate: boolean
  onToggleAutoRotate: () => void
  onReset: () => void
}) {
  return (
    <div className="absolute bottom-3 left-1/2 z-10 flex -translate-x-1/2 gap-2">
      <button type="button" onClick={onReset} className="btn-ghost !px-3 !py-1.5 !text-xs">
        重置视角
      </button>
      <button type="button" onClick={onToggleAutoRotate} className="btn-ghost !px-3 !py-1.5 !text-xs">
        {autoRotate ? '停止旋转' : '自动旋转'}
      </button>
    </div>
  )
}

export function PorcelainViewer(props: PorcelainViewerProps) {
  const {
    modelUrl,
    heatmapUrl,
    showHeatmap = false,
    shape,
    glaze,
    interactive = true,
    showControls = false,
    parts,
    selectedPartId,
    onPartSelect,
    className,
    resetToken = 0,
    viewId,
    syncEnabled,
    syncRef,
    framingRadius,
    focusRegion,
    normalizeModel = false,
  } = props

  const [autoRotate, setAutoRotate] = useState(props.autoRotate ?? false)
  const [localReset, setLocalReset] = useState(0)
  const controlsRef = useRef<OrbitControlsImpl | null>(null)

  const resolvedShape = shape ?? DEFAULT_SHAPE
  const resolvedGlaze = glaze ?? DEFAULT_GLAZE

  const bounds = useMemo(() => computeBounds(resolvedShape), [resolvedShape])
  const targetY = (bounds.maxY + bounds.minY) / 2
  const cameraDistance = Math.max((framingRadius ?? bounds.maxR) * 4.5, bounds.maxY * 1.9, 38)

  const selectedPart = parts?.find((p) => p.id === selectedPartId)
  const highlightRegion = focusRegion ?? (selectedPart ? { yMin: selectedPart.yMin, yMax: selectedPart.yMax } : undefined)

  const handleChange = () => {
    const c = controlsRef.current
    if (!c || !syncEnabled || !syncRef || !viewId) return
    if (syncRef.current?.from !== viewId) return
    const cam = c.object as THREE.PerspectiveCamera
    syncRef.current = {
      position: [cam.position.x, cam.position.y, cam.position.z],
      target: [c.target.x, c.target.y, c.target.z],
      from: viewId,
      anchorY: focusRegion ? (focusRegion.yMin + focusRegion.yMax)/2 : targetY,
    }
  }

  const vessel = (
    <Vessel
      shape={resolvedShape}
      glaze={resolvedGlaze}
      highlightRegion={highlightRegion}
      parts={parts}
      onPartSelect={onPartSelect}
    />
  )

  return (
    <div className={'relative ' + (className ?? 'h-full w-full')}>
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [0, targetY, cameraDistance], fov: 40 }}
        gl={{ antialias: true, alpha: true, localClippingEnabled: true }}
      >
        <ambientLight intensity={1.4} />
        <hemisphereLight args={['#ffffff', '#d8d2c2', 0.7]} />
        <directionalLight position={[6, 10, 6]} intensity={1.9} />
        <directionalLight position={[-6, 4, -5]} intensity={0.7} color="#cfe0e8" />
        <pointLight position={[0, targetY + 6, 6]} intensity={0.5} color="#ffffff" />

        <Suspense fallback={<LoadingFallback />}>
          {modelUrl && (
            <ModelErrorBoundary key={modelUrl} fallback={normalizeModel ? <Html center><p className="whitespace-nowrap text-sm">模型加载失败，请重新导入</p></Html> : vessel}>
              <GLTFModel url={modelUrl} visible={!showHeatmap} normalize={normalizeModel} region={highlightRegion} />
            </ModelErrorBoundary>
          )}
          {heatmapUrl && (
            <ModelErrorBoundary fallback={null}>
              <GLTFModel url={heatmapUrl} visible={showHeatmap} />
            </ModelErrorBoundary>
          )}
          {!modelUrl && !heatmapUrl && vessel}
        </Suspense>

        {/* 展台 */}
        <mesh position={[0, -0.45, 0]} receiveShadow>
          <cylinderGeometry args={[bounds.maxR * 1.35, bounds.maxR * 1.6, 0.9, 64]} />
          <meshStandardMaterial color="#1e2a3a" roughness={0.85} metalness={0.08} />
        </mesh>

        <ContactShadows
          position={[0, 0.02, 0]}
          opacity={0.35}
          scale={bounds.maxR * 5}
          blur={2.6}
          far={3}
          resolution={512}
          color="#1e2a3a"
        />

        <OrbitControls
          ref={controlsRef}
          makeDefault
          target={[0, targetY, 0]}
          enablePan={false}
          enableRotate={interactive}
          enableZoom={interactive}
          minDistance={(framingRadius ?? bounds.maxR) * 2.2}
          maxDistance={cameraDistance * 2.2}
          autoRotate={autoRotate}
          autoRotateSpeed={1.1}
          onChange={handleChange}
          onStart={() => {
            const c = controlsRef.current
            if (c && syncEnabled && syncRef && viewId) {
              syncRef.current = { position: [c.object.position.x,c.object.position.y,c.object.position.z],
                target: [c.target.x,c.target.y,c.target.z], from: viewId,
                anchorY: focusRegion ? (focusRegion.yMin+focusRegion.yMax)/2 : targetY }
            }
          }}
        />

        <Rig
          bounds={bounds}
          resetToken={resetToken + localReset}
          cameraDistance={cameraDistance}
          controlsRef={controlsRef}
          syncEnabled={syncEnabled}
          syncRef={syncRef}
          viewId={viewId}
          focusRegion={focusRegion}
        />
      </Canvas>

      {showControls && (
        <ViewerControls
          autoRotate={autoRotate}
          onToggleAutoRotate={() => setAutoRotate((v) => !v)}
          onReset={() => setLocalReset((v) => v + 1)}
        />
      )}
    </div>
  )
}

export default PorcelainViewer
