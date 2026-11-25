import { Suspense, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { Canvas, useThree } from '@react-three/fiber'
import { ContactShadows, OrbitControls, useGLTF } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

/** 加载 GLB 并按自身包围盒居中，底部落在 y=0，保证不同引擎模型取景一致。 */
function CenteredModel({ url }: { url: string }) {
  const { scene: original } = useGLTF(url)
  const { scene, center, size } = useMemo(() => {
    const cloned = original.clone(true)
    const box = new THREE.Box3().setFromObject(cloned)
    const c = box.getCenter(new THREE.Vector3())
    const s = box.getSize(new THREE.Vector3())
    cloned.position.x -= c.x
    cloned.position.z -= c.z
    cloned.position.y -= box.min.y
    cloned.traverse((obj) => {
      const mesh = obj as THREE.Mesh
      if (mesh.isMesh) {
        mesh.castShadow = true
        mesh.receiveShadow = true
      }
    })
    return { scene: cloned, center: c, size: s }
  }, [original])

  return (
    <group>
      <primitive object={scene} />
      <CameraRig size={size} />
    </group>
  )
}

function CameraRig({ size }: { size: THREE.Vector3 }) {
  const { camera } = useThree()
  const controlsRef = useRef<OrbitControlsImpl | null>(null)
  const maxDim = Math.max(size.x, size.y, size.z) || 1
  useMemo(() => {
    const dist = maxDim * 2.1
    camera.position.set(dist * 0.5, dist * 0.7, dist)
    camera.near = maxDim / 100
    camera.far = maxDim * 100
    camera.updateProjectionMatrix()
  }, [camera, maxDim])
  return (
    <OrbitControls
      ref={controlsRef}
      target={[0, size.y / 2, 0]}
      enableDamping
      dampingFactor={0.08}
    />
  )
}

export function ModelCompareViewer({ url }: { url: string }) {
  return (
    <Canvas
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
      camera={{ fov: 40 }}
    >
      <ambientLight intensity={1.3} />
      <hemisphereLight args={['#ffffff', '#d8d2c2', 0.7]} />
      <directionalLight position={[5, 8, 5]} intensity={1.6} />
      <directionalLight position={[-5, 4, -4]} intensity={0.5} />
      <Suspense fallback={null}>
        <CenteredModel url={url} />
        <ContactShadows position={[0, 0, 0]} opacity={0.3} scale={12} blur={2.4} far={4} />
      </Suspense>
    </Canvas>
  )
}

export default ModelCompareViewer
