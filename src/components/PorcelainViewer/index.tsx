import {
  Component,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { MutableRefObject, ReactNode } from 'react'
import * as THREE from 'three'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { ContactShadows, Html, OrbitControls, useGLTF } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { createGlazeTexture } from './textures'
import type {
  GlazeStyle,
  PorcelainPart,
  PorcelainShape,
} from '../../types/porcelain'

export interface SyncState {
  position: [number, number, number]
  target: [number, number, number]
  from: string
}

export interface PorcelainViewerProps {
  /** 未来后端返回的 GLB 地址，优先于 shape 使用；加载失败时回退到程序化轮廓 */
  modelUrl?: string
  photoTexture?: boolean
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

function computeBounds(shape: PorcelainShape): {
  minY: number
  maxY: number
  maxR: number
} {
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

function segmentProfile(
  shape: PorcelainShape,
  yMin: number,
  yMax: number,
): PorcelainShape {
  const sorted = [...shape].sort((a, b) => a[1] - b[1])
  const pts: PorcelainShape = [[radiusAt(shape, yMin) * 1.015, yMin]]
  for (const [x, y] of sorted) {
    if (y > yMin && y < yMax) pts.push([x * 1.015, y])
  }
  pts.push([radiusAt(shape, yMax) * 1.015, yMax])
  return pts
}

function findPart(
  parts: PorcelainPart[] | undefined,
  y: number,
): PorcelainPart | undefined {
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

  const texture = useMemo(
    () => createGlazeTexture(glaze.decoration),
    [glaze.decoration],
  )

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
      {highlightRegion && (
        <HighlightSegment shape={shape} region={highlightRegion} />
      )}
    </group>
  )
}

function HighlightSegment({
  shape,
  region,
}: {
  shape: PorcelainShape
  region: { yMin: number; yMax: number }
}) {
  return (
    <group>
      {[region.yMin, region.yMax].map((y) => (
        <mesh
          key={y}
          position={[0, y, 0]}
          rotation={[Math.PI / 2, 0, 0]}
          raycast={() => {}}
          renderOrder={2}
        >
          <torusGeometry args={[radiusAt(shape, y) * 1.005, 0.045, 6, 128]} />
          <meshBasicMaterial color="#c9a96b" toneMapped={false} />
        </mesh>
      ))}
    </group>
  )
}

function GLTFModel({
  url,
  visible = true,
  parts,
  onPartSelect,
  region,
}: {
  url: string
  visible?: boolean
  parts?: PorcelainPart[]
  onPartSelect?: (id: string) => void
  region?: { yMin: number; yMax: number }
}) {
  const { scene: original } = useGLTF(url)
  const scene = useMemo(() => {
    const cloned = original.clone(true)
    cloned.traverse((obj) => {
      const mesh = obj as THREE.Mesh
      if (mesh.isMesh) {
        mesh.material = Array.isArray(mesh.material)
          ? mesh.material.map((m) => m.clone())
          : mesh.material.clone()
      }
    })
    return cloned
  }, [original])
  useEffect(() => {
    scene.visible = visible
    scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh
      if ((mesh as { isMesh?: boolean }).isMesh) {
        const mats = Array.isArray(mesh.material)
          ? mesh.material
          : [mesh.material]
        mats.forEach((mat) => {
          const m = mat as THREE.MeshStandardMaterial
          if (m && m.isMaterial) {
            m.vertexColors = !!mesh.geometry.getAttribute('color')
            m.side = THREE.DoubleSide
            if ((mat as THREE.MeshBasicMaterial).isMeshBasicMaterial)
              m.toneMapped = false
            m.onBeforeCompile = (shader) => {
              if (!region) return
              shader.vertexShader = shader.vertexShader
                .replace(
                  '#include <common>',
                  '#include <common>\nvarying float qjqnY;',
                )
                .replace(
                  '#include <begin_vertex>',
                  '#include <begin_vertex>\nqjqnY=(modelMatrix*vec4(transformed,1.0)).y;',
                )
              shader.fragmentShader = shader.fragmentShader
                .replace(
                  '#include <common>',
                  '#include <common>\nvarying float qjqnY;',
                )
                .replace(
                  '#include <color_fragment>',
                  `#include <color_fragment>\nif(abs(qjqnY-${region.yMin.toFixed(4)})<0.09 || abs(qjqnY-${region.yMax.toFixed(4)})<0.09) diffuseColor.rgb=mix(diffuseColor.rgb,vec3(0.79,0.66,0.35),0.8);`,
                )
            }
            m.customProgramCacheKey = () =>
              region ? `qjqn-${region.yMin}-${region.yMax}` : 'qjqn-base'
            m.needsUpdate = true
          }
        })
      }
    })
  }, [scene, visible, region?.yMin, region?.yMax])
  useEffect(
    () => () => {
      scene.traverse((obj) => {
        const mesh = obj as THREE.Mesh
        if (mesh.isMesh)
          (Array.isArray(mesh.material)
            ? mesh.material
            : [mesh.material]
          ).forEach((m) => m.dispose())
      })
    },
    [scene],
  )
  return (
    <primitive
      object={scene}
      onClick={(e: { point: THREE.Vector3; stopPropagation: () => void }) => {
        if (!visible) return
        e.stopPropagation()
        const part = findPart(parts, e.point.y)
        if (part) onPartSelect?.(part.id)
      }}
    />
  )
}

function LoadingFallback() {
  return (
    <Html center>
      <div className="whitespace-nowrap text-xs text-ink-soft">模型加载中…</div>
    </Html>
  )
}

class ModelErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { hasError: boolean }
> {
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
  focusPoint,
  focusY,
}: {
  bounds: { minY: number; maxY: number; maxR: number }
  resetToken: number
  cameraDistance: number
  controlsRef: MutableRefObject<OrbitControlsImpl | null>
  syncEnabled?: boolean
  syncRef?: MutableRefObject<SyncState | null>
  viewId?: string
  focusPoint?: [number, number, number]
  focusY?: number
}) {
  const { camera } = useThree()
  const lastFocusY = useRef(focusY)
  useEffect(() => {
    if (
      !controlsRef.current ||
      focusY === undefined ||
      lastFocusY.current === focusY
    )
      return
    lastFocusY.current = focusY
    const target = new THREE.Vector3(0, focusY, 0)
    const direction = camera.position
      .clone()
      .sub(controlsRef.current.target)
      .normalize()
    camera.position.copy(
      target
        .clone()
        .addScaledVector(
          direction,
          Math.max(bounds.maxR * 2.4, (bounds.maxY - bounds.minY) * 0.85),
        ),
    )
    controlsRef.current.target.copy(target)
    controlsRef.current.update()
  }, [focusY, camera, controlsRef, bounds])
  useEffect(() => {
    if (!focusPoint || !controlsRef.current) return
    const target = new THREE.Vector3(...focusPoint)
    const direction = camera.position
      .clone()
      .sub(controlsRef.current.target)
      .normalize()
    camera.position.copy(
      target
        .clone()
        .addScaledVector(
          direction,
          Math.max(bounds.maxR * 2.4, (bounds.maxY - bounds.minY) * 0.85),
        ),
    )
    controlsRef.current.target.copy(target)
    controlsRef.current.update()
  }, [focusPoint, camera, controlsRef, bounds])

  useEffect(() => {
    if (resetToken <= 0) return
    const targetY = (bounds.maxY + bounds.minY) / 2
    camera.position.set(0, targetY, cameraDistance)
    if (controlsRef.current) {
      controlsRef.current.target.set(0, targetY, 0)
      controlsRef.current.update()
    }
  }, [resetToken, bounds, cameraDistance, camera, controlsRef])

  useFrame(() => {
    if (!syncEnabled || !syncRef?.current || !controlsRef.current) return
    const s = syncRef.current
    if (s.from === viewId) return
    camera.position.lerp(
      _v1.set(s.position[0], s.position[1], s.position[2]),
      0.35,
    )
    controlsRef.current.target.lerp(
      _v2.set(s.target[0], s.target[1], s.target[2]),
      0.35,
    )
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
      <button
        type="button"
        onClick={onReset}
        className="btn-ghost !px-3 !py-1.5 !text-xs"
      >
        重置视角
      </button>
      <button
        type="button"
        onClick={onToggleAutoRotate}
        className="btn-ghost !px-3 !py-1.5 !text-xs"
      >
        {autoRotate ? '停止旋转' : '自动旋转'}
      </button>
    </div>
  )
}

export function PorcelainViewer(props: PorcelainViewerProps) {
  const {
    modelUrl,
    photoTexture = false,
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
  } = props

  const [autoRotate, setAutoRotate] = useState(props.autoRotate ?? false)
  const [localReset, setLocalReset] = useState(0)
  const [unobservedView, setUnobservedView] = useState(false)
  const [focusPoint, setFocusPoint] = useState<[number, number, number]>()
  const controlsRef = useRef<OrbitControlsImpl | null>(null)

  const resolvedShape = shape ?? DEFAULT_SHAPE
  const resolvedGlaze = glaze ?? DEFAULT_GLAZE

  const bounds = useMemo(() => computeBounds(resolvedShape), [resolvedShape])
  const targetY = (bounds.maxY + bounds.minY) / 2
  const cameraDistance = Math.max(bounds.maxR * 4.5, bounds.maxY * 1.9, 38)

  const selectedPart = parts?.find((p) => p.id === selectedPartId)
  const highlightRegion = selectedPart
    ? { yMin: selectedPart.yMin, yMax: selectedPart.yMax }
    : undefined

  const handleChange = () => {
    const c = controlsRef.current
    if (c && photoTexture)
      setUnobservedView(c.object.position.z - c.target.z < 0)
    if (!c || !syncEnabled || !syncRef || !viewId) return
    const cam = c.object as THREE.PerspectiveCamera
    syncRef.current = {
      position: [cam.position.x, cam.position.y, cam.position.z],
      target: [c.target.x, c.target.y, c.target.z],
      from: viewId,
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
        dpr={[1, 1.5]}
        camera={{ position: [0, targetY, cameraDistance], fov: 40 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={1.4} />
        <hemisphereLight args={['#ffffff', '#d8d2c2', 0.7]} />
        <directionalLight position={[6, 10, 6]} intensity={1.9} />
        <directionalLight
          position={[-6, 4, -5]}
          intensity={0.7}
          color="#cfe0e8"
        />
        <pointLight
          position={[0, targetY + 6, 6]}
          intensity={0.5}
          color="#ffffff"
        />

        <Suspense fallback={<LoadingFallback />}>
          <group
            onDoubleClick={(e) => {
              e.stopPropagation()
              setFocusPoint([e.point.x, e.point.y, e.point.z])
            }}
          >
            {modelUrl && (
              <ModelErrorBoundary
                key={modelUrl}
                fallback={
                  <Html center>
                    <span className="text-xs">
                      模型加载失败，请刷新后重试。
                    </span>
                  </Html>
                }
              >
                <GLTFModel
                  url={modelUrl}
                  visible={!showHeatmap}
                  parts={parts}
                  onPartSelect={onPartSelect}
                  region={highlightRegion}
                />
              </ModelErrorBoundary>
            )}
            {heatmapUrl && (
              <ModelErrorBoundary fallback={null}>
                <GLTFModel
                  url={heatmapUrl}
                  visible={showHeatmap}
                  parts={parts}
                  onPartSelect={onPartSelect}
                  region={highlightRegion}
                />
              </ModelErrorBoundary>
            )}
            {!modelUrl && !heatmapUrl && vessel}
          </group>
        </Suspense>

        {/* 展台 */}
        <mesh position={[0, -0.45, 0]} receiveShadow>
          <cylinderGeometry
            args={[bounds.maxR * 1.35, bounds.maxR * 1.6, 0.9, 64]}
          />
          <meshStandardMaterial
            color="#1e2a3a"
            roughness={0.85}
            metalness={0.08}
          />
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
          enablePan={interactive}
          enableRotate={interactive}
          enableZoom={interactive}
          minDistance={bounds.maxR * 2.2}
          maxDistance={cameraDistance * 2.2}
          autoRotate={autoRotate}
          autoRotateSpeed={1.1}
          onChange={handleChange}
        />

        <Rig
          bounds={bounds}
          resetToken={resetToken + localReset}
          cameraDistance={cameraDistance}
          controlsRef={controlsRef}
          syncEnabled={syncEnabled}
          syncRef={syncRef}
          viewId={viewId}
          focusPoint={focusPoint}
          focusY={
            selectedPart
              ? (selectedPart.yMin + selectedPart.yMax) / 2
              : undefined
          }
        />
      </Canvas>
      {photoTexture && unobservedView && (
        <span className="absolute right-3 top-3 rounded bg-paper/90 px-3 py-2 text-xs text-ink-soft">
          背面采用正面镜像纹理
        </span>
      )}

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
