"use client";

import { useEffect, useRef } from "react";
import {
  FilesetResolver,
  HandLandmarker,
} from "@mediapipe/tasks-vision";
import type { GestureState } from "./gesture-types";

interface HandGestureControllerProps {
  enabled: boolean;
  gestureStateRef: React.MutableRefObject<GestureState>;
}

const WASM_PATH =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm";

const MODEL_PATH =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

function distance(
  a: { x: number; y: number },
  b: { x: number; y: number },
) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function classifyGesture(
  landmarks: Array<{ x: number; y: number; z: number }>,
) {
  const wrist = landmarks[0];

  const thumbMcp = landmarks[2];
  const thumbIp = landmarks[3];
  const thumbTip = landmarks[4];

  const indexMcp = landmarks[5];
  const indexTip = landmarks[8];

  const middleMcp = landmarks[9];
  const middleTip = landmarks[12];

  const ringMcp = landmarks[13];
  const ringTip = landmarks[16];

  const pinkyMcp = landmarks[17];
  const pinkyTip = landmarks[20];

  const pinchDistance = distance(thumbTip, indexTip);

  if (pinchDistance < 0.065) {
    return {
      gesture: "pinch" as const,
      pinchDistance,
    };
  }

  const indexExtended =
    distance(indexTip, wrist) >
    distance(indexMcp, wrist) * 1.35;

  const middleExtended =
    distance(middleTip, wrist) >
    distance(middleMcp, wrist) * 1.35;

  const ringExtended =
    distance(ringTip, wrist) >
    distance(ringMcp, wrist) * 1.25;

  const pinkyExtended =
    distance(pinkyTip, wrist) >
    distance(pinkyMcp, wrist) * 1.25;

  const extendedCount = [
    indexExtended,
    middleExtended,
    ringExtended,
    pinkyExtended,
  ].filter(Boolean).length;

  const otherFingersCurled =
    !middleExtended &&
    !ringExtended &&
    !pinkyExtended;

  const thumbUp =
    otherFingersCurled &&
    !indexExtended &&
    thumbTip.y < thumbMcp.y - 0.04 &&
    thumbTip.y < thumbIp.y - 0.015;

  if (thumbUp) {
    return {
      gesture: "thumbs_up" as const,
      pinchDistance,
    };
  }

  const thumbDown =
    otherFingersCurled &&
    !indexExtended &&
    thumbTip.y > thumbMcp.y + 0.04 &&
    thumbTip.y > thumbIp.y + 0.015;

  if (thumbDown) {
    return {
      gesture: "thumbs_down" as const,
      pinchDistance,
    };
  }

  if (
    indexExtended &&
    middleExtended &&
    !ringExtended &&
    !pinkyExtended
  ) {
    return {
      gesture: "two_fingers" as const,
      pinchDistance,
    };
  }

  if (
    indexExtended &&
    !middleExtended &&
    !ringExtended &&
    !pinkyExtended
  ) {
    return {
      gesture: "point" as const,
      pinchDistance,
    };
  }

  if (extendedCount >= 3) {
    return {
      gesture: "open_palm" as const,
      pinchDistance,
    };
  }

  if (extendedCount === 0) {
    return {
      gesture: "fist" as const,
      pinchDistance,
    };
  }

  return {
    gesture: "none" as const,
    pinchDistance,
  };
}

export default function HandGestureController({
  enabled,
  gestureStateRef,
}: HandGestureControllerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const landmarkerRef = useRef<HandLandmarker | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const previousHandRef = useRef<{ x: number; y: number } | null>(null);
  const previousPinchRef = useRef<number | null>(null);
  const previousDepthRef = useRef<number | null>(null);

  useEffect(() => {
    gestureStateRef.current.enabled = enabled;

    if (!enabled) {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }

      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;

      previousHandRef.current = null;
      previousPinchRef.current = null;
      previousDepthRef.current = null;

      gestureStateRef.current.gesture = "none";
      gestureStateRef.current.pinchActive = false;
      gestureStateRef.current.rotationX = 0;
      gestureStateRef.current.rotationY = 0;
      gestureStateRef.current.rotationActive = false;
      gestureStateRef.current.zoomDelta = 0;
      gestureStateRef.current.handDepth = 0;

      return;
    }

    let cancelled = false;

    const start = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 640 },
            height: { ideal: 480 },
          },
          audio: false,
        });

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;

        const video = videoRef.current;

        if (!video) {
          return;
        }

        video.srcObject = stream;
        await video.play();

        const vision = await FilesetResolver.forVisionTasks(WASM_PATH);

        const landmarker = await HandLandmarker.createFromOptions(
          vision,
          {
            baseOptions: {
              modelAssetPath: MODEL_PATH,
              delegate: "GPU",
            },
            runningMode: "VIDEO",
            numHands: 2,
            minHandDetectionConfidence: 0.6,
            minHandPresenceConfidence: 0.6,
            minTrackingConfidence: 0.6,
          },
        );

        if (cancelled) {
          landmarker.close();
          return;
        }

        landmarkerRef.current = landmarker;

        const processFrame = () => {
          if (
            cancelled ||
            !videoRef.current ||
            !landmarkerRef.current
          ) {
            return;
          }

          const currentVideo = videoRef.current;

          if (currentVideo.readyState >= 2) {
            const now = performance.now();

            const result =
              landmarkerRef.current.detectForVideo(
                currentVideo,
                now,
              );

            const landmarks = result.landmarks?.[0];

            if (landmarks) {
              const palm = landmarks[9];

              const currentHand = {
                x: palm.x,
                y: palm.y,
              };

              const previousHand =
                previousHandRef.current;

              let rotationX = 0;
              let rotationY = 0;

              let swipeGesture:
                | "swipe_left"
                | "swipe_right"
                | null = null;

              if (previousHand) {
                const deltaX =
                  currentHand.x - previousHand.x;

                const deltaY =
                  currentHand.y - previousHand.y;

                rotationY = deltaX * 7;
                rotationX = deltaY * 7;

                if (
                  Math.abs(deltaX) > 0.075 &&
                  Math.abs(deltaX) > Math.abs(deltaY) * 1.5
                ) {
                  swipeGesture =
                    deltaX > 0
                      ? "swipe_right"
                      : "swipe_left";
                }
              }

              previousHandRef.current = currentHand;

              const classification =
                classifyGesture(landmarks);

              const detectedGesture =
                swipeGesture ?? classification.gesture;

              const previousPinch =
                previousPinchRef.current;

              let zoomDelta = 0;

              const wrist = landmarks[0];
              const indexMcp = landmarks[5];
              const middleMcp = landmarks[9];
              const ringMcp = landmarks[13];
              const pinkyMcp = landmarks[17];

              const palmDepth =
                (
                  distance(wrist, indexMcp) +
                  distance(wrist, middleMcp) +
                  distance(wrist, ringMcp) +
                  distance(wrist, pinkyMcp)
                ) / 4;

              if (previousDepthRef.current !== null) {
                zoomDelta =
                  (palmDepth -
                    previousDepthRef.current) *
                  18;
              }

              previousDepthRef.current = palmDepth;

              previousPinchRef.current =
                classification.pinchDistance;

              gestureStateRef.current.gesture =
                detectedGesture;

              gestureStateRef.current.handX =
                currentHand.x;

              gestureStateRef.current.handY =
                currentHand.y;

              gestureStateRef.current.pinchDistance =
                classification.pinchDistance;

              gestureStateRef.current.pinchActive =
                classification.gesture === "pinch";

              gestureStateRef.current.rotationX =
                rotationX;

              gestureStateRef.current.rotationY =
                rotationY;

              gestureStateRef.current.rotationActive =
                Math.abs(rotationX) > 0.002 ||
                Math.abs(rotationY) > 0.002;

              gestureStateRef.current.zoomDelta =
                classification.gesture === "fist"
                  ? 0
                  : zoomDelta;

              gestureStateRef.current.handDepth =
                palmDepth;

              gestureStateRef.current.lastUpdate =
                now;
            } else {
              previousHandRef.current = null;
              previousPinchRef.current = null;

              gestureStateRef.current.gesture = "none";
              gestureStateRef.current.pinchActive =
                false;
              gestureStateRef.current.rotationX = 0;
              gestureStateRef.current.rotationY = 0;
              gestureStateRef.current.rotationActive = false;
              gestureStateRef.current.zoomDelta = 0;
              gestureStateRef.current.handDepth = 0;
            }
          }

          animationFrameRef.current =
            requestAnimationFrame(processFrame);
        };

        animationFrameRef.current =
          requestAnimationFrame(processFrame);
      } catch (error) {
        console.error(
          "GROOT GESTURE ERROR:",
          error,
        );

        gestureStateRef.current.enabled = false;
        gestureStateRef.current.gesture = "none";
      }
    };

    void start();

    return () => {
      cancelled = true;

      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(
          animationFrameRef.current,
        );
        animationFrameRef.current = null;
      }

      landmarkerRef.current?.close();
      landmarkerRef.current = null;

      streamRef.current
        ?.getTracks()
        .forEach((track) => track.stop());

      streamRef.current = null;
    };
  }, [enabled, gestureStateRef]);

  return (
    <video
      ref={videoRef}
      muted
      playsInline
      autoPlay
      aria-hidden="true"
      style={{
        position: "fixed",
        width: 1,
        height: 1,
        opacity: 0,
        pointerEvents: "none",
      }}
    />
  );
}
