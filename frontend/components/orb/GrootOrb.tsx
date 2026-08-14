"use client";

import type { MutableRefObject } from "react";
import type { GestureState } from "@/components/gestures/gesture-types";

import { OrbitControls } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import type { ComponentRef } from "react";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

const GOLD = "#d9a62e";
const AMBER = "#ffb21c";
const BRIGHT = "#ffdc73";
const PALE = "#fff3bc";

type Vector3Tuple = [number, number, number];

type ParticleFieldProps = {
  count: number;
  radiusMin: number;
  radiusMax: number;
  size: number;
  opacity: number;
  seed: number;
  spin: Vector3Tuple;
};

type OrbitalRingConfig = {
  radius: number;
  tube: number;
  rotation: Vector3Tuple;
  speed: number;
  opacity: number;
  phase: number;
};

const ORBITAL_RINGS: OrbitalRingConfig[] = [
  {
    radius: 1.42,
    tube: 0.008,
    rotation: [0.12, 0.18, 0.04],
    speed: 0.16,
    opacity: 0.48,
    phase: 0.3,
  },
  {
    radius: 1.55,
    tube: 0.011,
    rotation: [Math.PI / 2, 0.18, 0.2],
    speed: -0.12,
    opacity: 0.62,
    phase: 2.1,
  },
  {
    radius: 1.69,
    tube: 0.007,
    rotation: [0.78, 0.38, -0.24],
    speed: 0.1,
    opacity: 0.44,
    phase: 4.4,
  },
  {
    radius: 1.82,
    tube: 0.005,
    rotation: [1.18, -0.42, 0.35],
    speed: -0.07,
    opacity: 0.28,
    phase: 1.2,
  },
];

const BAND_LEVELS = Array.from(
  { length: 17 },
  (_, index) => -1.05 + index * 0.13125,
);

function createSeededRandom(seed: number) {
  let state = seed >>> 0;

  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function ParticleField({
  count,
  radiusMin,
  radiusMax,
  size,
  opacity,
  seed,
  spin,
}: ParticleFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);

  const { positions, colors } = useMemo(() => {
    const random = createSeededRandom(seed);
    const particlePositions = new Float32Array(count * 3);
    const particleColors = new Float32Array(count * 3);
    const lowColor = new THREE.Color(GOLD);
    const hotColor = new THREE.Color(PALE);
    const color = new THREE.Color();
    const minCube = radiusMin ** 3;
    const radiusRange = radiusMax ** 3 - minCube;

    for (let index = 0; index < count; index += 1) {
      const radius = Math.cbrt(minCube + random() * radiusRange);
      const cosPhi = random() * 2 - 1;
      const sinPhi = Math.sqrt(1 - cosPhi * cosPhi);
      const theta = random() * Math.PI * 2;
      const offset = index * 3;

      particlePositions[offset] = radius * sinPhi * Math.cos(theta);
      particlePositions[offset + 1] = radius * cosPhi;
      particlePositions[offset + 2] = radius * sinPhi * Math.sin(theta);

      color.copy(lowColor).lerp(hotColor, random() ** 3);
      particleColors[offset] = color.r;
      particleColors[offset + 1] = color.g;
      particleColors[offset + 2] = color.b;
    }

    return {
      positions: particlePositions,
      colors: particleColors,
    };
  }, [count, radiusMax, radiusMin, seed]);

  useFrame((_, delta) => {
    if (!pointsRef.current) {
      return;
    }

    pointsRef.current.rotation.x += delta * spin[0];
    pointsRef.current.rotation.y += delta * spin[1];
    pointsRef.current.rotation.z += delta * spin[2];
  });

  return (
    <points ref={pointsRef} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        vertexColors
        size={size}
        transparent
        opacity={opacity}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        toneMapped={false}
      />
    </points>
  );
}
function DataFilaments() {
  const linesRef = useRef<THREE.LineSegments>(null);

  const positions = useMemo(() => {
    const random = createSeededRandom(714);
    const segmentCount = 420;
    const data = new Float32Array(segmentCount * 6);

    for (let index = 0; index < segmentCount; index += 1) {
      const radius = 0.5 + random() * 0.78;
      const cosPhi = random() * 2 - 1;
      const sinPhi = Math.sqrt(1 - cosPhi * cosPhi);
      const theta = random() * Math.PI * 2;
      const x = radius * sinPhi * Math.cos(theta);
      const y = radius * cosPhi;
      const z = radius * sinPhi * Math.sin(theta);
      const length = 0.025 + random() * 0.095;
      const offset = index * 6;

      data[offset] = x;
      data[offset + 1] = y;
      data[offset + 2] = z;
      data[offset + 3] = x + (random() - 0.5) * length;
      data[offset + 4] = y + (random() - 0.5) * length;
      data[offset + 5] = z + (random() - 0.5) * length;
    }

    return data;
  }, []);

  useFrame((_, delta) => {
    if (linesRef.current) {
      linesRef.current.rotation.y -= delta * 0.045;
      linesRef.current.rotation.z += delta * 0.008;
    }
  });

  return (
    <lineSegments ref={linesRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color={BRIGHT}
        transparent
        opacity={0.3}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        toneMapped={false}
      />
    </lineSegments>
  );
}

function LayeredShells() {
  const shellRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (shellRef.current) {
      shellRef.current.rotation.y -= delta * 0.022;
      shellRef.current.rotation.x += delta * 0.004;
    }
  });

  return (
    <group ref={shellRef}>
      <mesh>
        <sphereGeometry args={[1.34, 56, 36]} />
        <meshBasicMaterial
          color={GOLD}
          wireframe
          transparent
          opacity={0.11}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh rotation={[0.38, 0.24, 0.12]}>
        <icosahedronGeometry args={[1.27, 3]} />
        <meshBasicMaterial
          color={BRIGHT}
          wireframe
          transparent
          opacity={0.075}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh rotation={[0.82, -0.32, 0.3]}>
        <sphereGeometry args={[1.14, 28, 20]} />
        <meshBasicMaterial
          color={AMBER}
          wireframe
          transparent
          opacity={0.1}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh>
        <sphereGeometry args={[1.37, 36, 24]} />
        <meshBasicMaterial
          color={AMBER}
          transparent
          opacity={0.018}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.BackSide}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}

function LatitudeBands() {
  const bandsRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (bandsRef.current) {
      bandsRef.current.rotation.y += delta * 0.07;
    }
  });

  return (
    <group ref={bandsRef}>
      {BAND_LEVELS.map((y, index) => {
        const radius = Math.sqrt(Math.max(0.03, 1.17 ** 2 - y ** 2));
        const highlighted = index % 4 === 0;
        const arc = Math.PI * (index % 2 === 0 ? 1.52 : 1.15);

        return (
          <mesh
            key={y}
            position={[0, y, 0]}
            rotation={[Math.PI / 2, 0, index * 0.71]}
          >
            <torusGeometry
              args={[
                radius,
                highlighted ? 0.008 : 0.0035,
                5,
                120,
                arc,
              ]}
            />
            <meshBasicMaterial
              color={highlighted ? BRIGHT : GOLD}
              transparent
              opacity={highlighted ? 0.28 : 0.13}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
              toneMapped={false}
            />
          </mesh>
        );
      })}
    </group>
  );
}

function OrbitalRing({
  radius,
  tube,
  rotation,
  speed,
  opacity,
  phase,
}: OrbitalRingConfig) {
  const ringRef = useRef<THREE.Group>(null);
  const nodeAngles = [phase, phase + Math.PI * 1.17];

  useFrame((_, delta) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * speed;
      ringRef.current.rotation.x += delta * speed * 0.045;
      ringRef.current.rotation.y += delta * speed * 0.08;
    }
  });

  return (
    <group ref={ringRef} rotation={rotation}>
      <mesh>
        <torusGeometry args={[radius, tube, 8, 220]} />
        <meshBasicMaterial
          color={GOLD}
          transparent
          opacity={opacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh rotation={[0, 0, phase]}>
        <torusGeometry
          args={[radius, tube * 2.15, 8, 100, Math.PI * 0.56]}
        />
        <meshBasicMaterial
          color={BRIGHT}
          transparent
          opacity={Math.min(0.92, opacity + 0.2)}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      {nodeAngles.map((angle) => (
        <mesh
          key={angle}
          position={[Math.cos(angle) * radius, Math.sin(angle) * radius, 0]}
        >
          <sphereGeometry args={[tube * 3.2, 12, 12]} />
          <meshBasicMaterial
            color={PALE}
            transparent
            opacity={0.9}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
            toneMapped={false}
          />
        </mesh>
      ))}
    </group>
  );
}

function OrbitalSystem() {
  return (
    <>
      {ORBITAL_RINGS.map((ring) => (
        <OrbitalRing key={ring.radius} {...ring} />
      ))}
    </>
  );
}

function EnergyCore({ speaking }: { speaking: boolean }) {
  const pulseRef = useRef<THREE.Group>(null);
  const latticeRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    const time = state.clock.elapsedTime;

    const idlePulse =
      1 + Math.sin(time * 2.6) * 0.055;

    const speechPulse = speaking
      ? 1 + Math.sin(time * 8.5) * 0.18
      : idlePulse;

    pulseRef.current?.scale.setScalar(
      THREE.MathUtils.lerp(
        pulseRef.current.scale.x,
        speechPulse,
        speaking ? 0.18 : 0.08,
      ),
    );

    if (latticeRef.current) {
      latticeRef.current.rotation.x += delta * 0.09;
      latticeRef.current.rotation.y -= delta * 0.12;
    }
  });

  return (
    <group>
      <group ref={pulseRef}>
        <mesh>
          <sphereGeometry args={[0.29, 48, 48]} />
          <meshBasicMaterial
            color={PALE}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
            toneMapped={false}
          />
        </mesh>

        <mesh>
          <sphereGeometry args={[0.43, 40, 40]} />
          <meshBasicMaterial
            color={BRIGHT}
            transparent
            opacity={0.33}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
            side={THREE.BackSide}
            toneMapped={false}
          />
        </mesh>
      </group>

      <mesh ref={latticeRef}>
        <icosahedronGeometry args={[0.57, 2]} />
        <meshBasicMaterial
          color={BRIGHT}
          wireframe
          transparent
          opacity={0.52}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh rotation={[0.3, 0.5, 0.15]}>
        <sphereGeometry args={[0.75, 24, 18]} />
        <meshBasicMaterial
          color={GOLD}
          wireframe
          transparent
          opacity={0.12}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}

function ScanningBand() {
  const scanRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (!scanRef.current) {
      return;
    }

    const y = ((state.clock.elapsedTime * 0.34) % 2.5) - 1.25;
    const radius = Math.sqrt(Math.max(0.015, 1 - (y / 1.28) ** 2)) * 1.3;

    scanRef.current.position.y = y;
    scanRef.current.scale.set(radius, radius, 1);
  });

  return (
    <group ref={scanRef} rotation={[Math.PI / 2, 0, 0]}>
      <mesh>
        <torusGeometry args={[1, 0.008, 6, 144]} />
        <meshBasicMaterial
          color={PALE}
          transparent
          opacity={0.58}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
      <mesh>
        <torusGeometry args={[1, 0.035, 8, 144]} />
        <meshBasicMaterial
          color={AMBER}
          transparent
          opacity={0.08}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}

function GrootCore({ speaking }: { speaking: boolean }) {
  const coreRef = useRef<THREE.Group>(null);

  useFrame((state, delta) => {
    if (coreRef.current) {
      coreRef.current.rotation.y += delta * 0.026;
      coreRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.16) * 0.025;
    }
  });

  return (
    <group ref={coreRef}>
      <LayeredShells />
      <ParticleField
        count={5200}
        radiusMin={0.4}
        radiusMax={1.28}
        size={0.011}
        opacity={0.72}
        seed={4021}
        spin={[0.008, -0.032, 0.004]}
      />
      <DataFilaments />
      <LatitudeBands />
      <OrbitalSystem />
      <EnergyCore speaking={speaking} />
      <ScanningBand />
    </group>
  );
}

function Scene({ speaking }: { speaking: boolean }) {
  return (
    <>
      <color attach="background" args={["#000000"]} />
      <GrootCore speaking={speaking} />

      <ParticleField
        count={1350}
        radiusMin={2.15}
        radiusMax={5.2}
        size={0.015}
        opacity={0.4}
        seed={9163}
        spin={[0.003, 0.012, -0.002]}
      />

      <EffectComposer>
        <Bloom
          intensity={1.55}
          luminanceThreshold={0.12}
          luminanceSmoothing={0.78}
          mipmapBlur
        />
      </EffectComposer>
    </>
  );
}

function CameraControls({
  resetSignal,
  gestureStateRef,
  responseMode = false,
}: {
  resetSignal: number;
  gestureStateRef?: MutableRefObject<GestureState>;
  responseMode?: boolean;
}) {
  const controlsRef = useRef<ComponentRef<typeof OrbitControls>>(null);

  const { camera } = useThree();

  useEffect(() => {
    if (resetSignal > 0) {
      controlsRef.current?.reset();

      if (gestureStateRef?.current) {
        gestureStateRef.current.rotationX = 0;
        gestureStateRef.current.rotationY = 0;
        gestureStateRef.current.rotationActive = false;
        gestureStateRef.current.zoomDelta = 0;
      }
    }
  }, [resetSignal, gestureStateRef]);

  useFrame(() => {
    const controls = controlsRef.current;
    const gesture = gestureStateRef?.current;

    if (!controls) {
      return;
    }

    if (responseMode) {
      const desiredCamera = new THREE.Vector3(
        -1.55,
        0.85,
        7.2,
      );

      const desiredTarget = new THREE.Vector3(
        -1.55,
        0.85,
        0,
      );

      camera.position.lerp(
        desiredCamera,
        0.035,
      );

      controls.target.lerp(
        desiredTarget,
        0.035,
      );

      camera.lookAt(controls.target);
    }

    if (!gesture || !gesture.enabled) {
      return;
    }

    if (gesture.pinchActive && Math.abs(gesture.zoomDelta) > 0.0001) {
      const target = controls.target;

      const offset = camera.position.clone().sub(target);
      const distance = offset.length();

      const nextDistance = THREE.MathUtils.clamp(
        distance - gesture.zoomDelta * 0.30,
        0.28,
        9,
      );

      offset.setLength(nextDistance);
      camera.position.copy(target).add(offset);
      camera.lookAt(target);

      controls.update();
      return;
    }

    if (!gesture.rotationActive) {
      return;
    }

    const target = controls.target;

    const offset = camera.position.clone().sub(target);

    const spherical = new THREE.Spherical().setFromVector3(offset);

    spherical.theta -= gesture.rotationY * 0.35;
    spherical.phi -= gesture.rotationX * 0.35;

    const epsilon = 0.001;

    spherical.phi = Math.max(
      epsilon,
      Math.min(Math.PI - epsilon, spherical.phi),
    );

    offset.setFromSpherical(spherical);

    camera.position.copy(target).add(offset);
    camera.lookAt(target);

    controls.update();
  });


  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enablePan={false}
      enableRotate
      enableZoom
      enableDamping
      dampingFactor={0.065}
      rotateSpeed={0.48}
      zoomSpeed={0.72}
      minDistance={0.28}
      maxDistance={9}
      target={[0, 0, 0]}
    />
  );
}

export default function GrootOrb({
  resetSignal = 0,
  gestureStateRef,
  frozen = false,
  speaking = false,
  responseMode = false,
  onOrbClick,
}: {
  resetSignal?: number;
  gestureStateRef?: MutableRefObject<GestureState>;
  frozen?: boolean;
  speaking?: boolean;
  responseMode?: boolean;
  onOrbClick?: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-0 h-screen w-screen overflow-hidden bg-black"
      aria-hidden="true"
    >
      <Canvas
        className="groot-canvas"
        frameloop={frozen ? "never" : "always"}
        camera={{
          position: [0, 0, 5],
          fov: 40,
          near: 0.008,
          far: 80,
        }}
        dpr={[1, 1.8]}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
        }}
        performance={{ min: 0.55 }}
        onCreated={({ gl }) => gl.setClearColor("#000000", 1)}
      >
        <group
          position={responseMode ? [-1.55, 0.85, 0] : [0, 0, 0]}
          scale={responseMode ? 0.58 : 1}
          onClick={(event) => {
            if (responseMode) {
              event.stopPropagation();
              onOrbClick?.();
            }
          }}
        >
          <Scene speaking={speaking} />
        </group>
        <CameraControls
          resetSignal={resetSignal}
          gestureStateRef={gestureStateRef}
          responseMode={responseMode}
        />
      </Canvas>
    </div>
  );
}
