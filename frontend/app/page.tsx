"use client";

import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import GrootOrb from "@/components/orb/GrootOrb";
import VoiceInput from "@/components/voice/VoiceInput";
import HandGestureController from "@/components/gestures/HandGestureController";
import type { GestureState } from "@/components/gestures/gesture-types";

function speakGrootResponse(
  text: string,
  onStart?: () => void,
  onEnd?: () => void,
) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    onEnd?.();
    return;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-GB";
  utterance.rate = 0.88;
  utterance.pitch = 0.72;
  utterance.volume = 1;

  const voices = window.speechSynthesis.getVoices();
  const britishVoice = voices.find(
    (voice) => voice.name === "Daniel" && voice.lang.startsWith("en-GB"),
  );

  if (britishVoice) {
    utterance.voice = britishVoice;
  }

  utterance.onstart = () => {
    onStart?.();
  };

  utterance.onend = () => {
    onEnd?.();
  };

  utterance.onerror = () => {
    onEnd?.();
  };

  window.speechSynthesis.speak(utterance);
}

export default function Home() {
  const [gesturesEnabled, setGesturesEnabled] = useState(false);
  const [gestureAction, setGestureAction] = useState("IDLE");
  const [orbFrozen, setOrbFrozen] = useState(false);
  const previousGestureRef = useRef<GestureState["gesture"]>("none");

  const gestureStateRef = useRef<GestureState>({
    enabled: false,
    gesture: "none",
    handX: 0.5,
    handY: 0.5,
    pinchDistance: 0,
    pinchActive: false,
    rotationX: 0,
    rotationY: 0,
    zoomDelta: 0,
    handDepth: 0,
    rotationActive: false,
    lastUpdate: 0,
  });
  const [resetSignal, setResetSignal] = useState(0);
  const [voiceResponse, setVoiceResponse] = useState("");
  const [voiceProcessing, setVoiceProcessing] = useState(false);
  const [responseMode, setResponseMode] = useState(false);
  const [grootSpeaking, setGrootSpeaking] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "g") {
        setGesturesEnabled((enabled) => !enabled);
      }

      if (event.key.toLowerCase() === "r") {
        setResetSignal((signal) => signal + 1);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (!gesturesEnabled) {
      previousGestureRef.current = "none";
      setOrbFrozen(false);
      return;
    }

    const interval = window.setInterval(() => {
      const gesture = gestureStateRef.current.gesture;
      const previous = previousGestureRef.current;

      if (gesture === previous) {
        return;
      }

      previousGestureRef.current = gesture;

      switch (gesture) {
        case "point":
          setGestureAction("FOCUS / SELECT");
          break;

        case "fist":
          setGestureAction("FREEZE / PAUSE");
          setOrbFrozen(true);
          break;

        case "open_palm":
          setGestureAction("WAKE / ACTIVATE");
          setOrbFrozen(false);
          break;

        case "thumbs_up":
          setGestureAction("CONFIRM / EXECUTE");
          break;

        case "thumbs_down":
          setGestureAction("CANCEL / REJECT");
          break;

        case "two_fingers":
          setGestureAction("SWITCH MODE");
          break;

        case "swipe_left":
          setGestureAction("CYCLE PREVIOUS");
          break;

        case "swipe_right":
          setGestureAction("CYCLE NEXT");
          break;

        case "none":
          setGestureAction("IDLE");
          break;

        case "pinch":
          break;
      }
    }, 50);

    return () => window.clearInterval(interval);
  }, [gesturesEnabled, gestureStateRef]);

  return (
    <main className="groot-interface">
      <GrootOrb
        resetSignal={resetSignal}
        gestureStateRef={gestureStateRef}
        frozen={orbFrozen}
        speaking={grootSpeaking}
        responseMode={responseMode}
        onOrbClick={() => {
          setResponseMode(false);
          setVoiceResponse("");
          setVoiceProcessing(false);
          setGrootSpeaking(false);
        }}
      />

      <HandGestureController
        enabled={gesturesEnabled}
        gestureStateRef={gestureStateRef}
      />

      <div className="ambient-overlay" aria-hidden="true" />
      <div className="scene-reticle" aria-hidden="true" />
      <div className="hud-frame" aria-hidden="true" />

      <header className="brand-lockup">
        <div className="hud-kicker">
          <span className="hud-kicker-line" />
          GROOT / CORE 01
        </div>
        <h1>GROOT</h1>
        <p>OPERATIONAL INTELLIGENCE</p>
      </header>

      <section className="system-readout" aria-label="System status">
        <div className="status-line" role="status">
          <span className="status-pulse" aria-hidden="true" />
          <span>SYSTEM ONLINE</span>
        </div>
        <p>HOLOGRAPHIC CORE / LOCAL</p>
        <span className="system-mode">IDLE — AWAITING INPUT</span>
      </section>

      <section className="interaction-guide" aria-label="Interaction controls">
        <p className="hud-section-label">DIRECT MANIPULATION</p>
        <ul>
          <li>
            <span className="hud-index">01</span>
            <span>
              <strong>DRAG</strong> ROTATE ORB
            </span>
          </li>
          <li>
            <span className="hud-index">02</span>
            <span>
              <strong>SCROLL / PINCH</strong> ZOOM
            </span>
          </li>
          <li>
            <span className="hud-index">03</span>
            <span>
              <strong>R</strong> RESET VIEW
            </span>
          </li>
        </ul>
      </section>

      <section className="scene-actions" aria-label="View controls">
        <span>VIEW / PERSPECTIVE</span>
        <button
          type="button"
          className="hud-button reset-button"
          onClick={() => setResetSignal((signal) => signal + 1)}
        >
          <span aria-hidden="true">↺</span>
          RESET VIEW
        </button>
      </section>

      <section className={`voice-panel ${responseMode ? "voice-panel-response" : ""}`} aria-label="Voice input">
        <VoiceInput
          onTranscript={async (transcript) => {
            setVoiceProcessing(true);
            setVoiceResponse("");

            try {
              const response = await fetch(
                `${process.env.NEXT_PUBLIC_AI_ENGINE_URL}/ai`,
                {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                  },
                  body: JSON.stringify({
                    user_id: uuidv4(),
                    organization_id: uuidv4(),
                    request_id: uuidv4(),
                    message: transcript,
                  }),
                },
              );

              if (!response.ok) {
                throw new Error(
                  `AI engine returned ${response.status}`,
                );
              }

              const data = await response.json();
              const responseText = data.text ?? "";

              setVoiceResponse(responseText);
              setResponseMode(true);

              if (responseText.trim()) {
                speakGrootResponse(
                  responseText,
                  () => setGrootSpeaking(true),
                  () => setGrootSpeaking(false),
                );
              }
            } catch (error) {
              console.error("GROOT VOICE ERROR:", error);
              setVoiceResponse("GROOT AI ENGINE UNAVAILABLE");
              setResponseMode(true);
            } finally {
              setVoiceProcessing(false);
            }
          }}
        />

        {(voiceProcessing || voiceResponse) && (
          <div className="voice-response">
            <span>
              {voiceProcessing
                ? "PROCESSING..."
                : "GROOT RESPONSE"}
            </span>

            {voiceResponse && (
              <p key={voiceResponse} className="voice-response-text">
                {voiceResponse}
              </p>
            )}
          </div>
        )}
      </section>

      <section className="gesture-panel" aria-label="Gesture input placeholder">
        <div className="gesture-copy">
          <span>MEDIAPIPE FOUNDATION</span>

          <strong>
            {gesturesEnabled
              ? gestureStateRef.current.gesture
                  .replace("_", " ")
                  .toUpperCase()
              : "GESTURES STANDBY"}
          </strong>

          <small>
            {gesturesEnabled
              ? gestureAction
              : "CAMERA INACTIVE"}
          </small>
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={gesturesEnabled}
          aria-label="Toggle gesture integration placeholder"
          className="gesture-toggle"
          onClick={() => setGesturesEnabled((enabled) => !enabled)}
        >
          <span className="toggle-track" aria-hidden="true">
            <span className="toggle-thumb" />
          </span>
          <span>{gesturesEnabled ? "ON" : "OFF"}</span>
        </button>
        <kbd>G</kbd>
      </section>
    </main>
  );
}
