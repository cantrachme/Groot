"use client";

import { useEffect, useState } from "react";
import GrootOrb from "@/components/orb/GrootOrb";

export default function Home() {
  const [gesturesEnabled, setGesturesEnabled] = useState(false);
  const [resetSignal, setResetSignal] = useState(0);

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

  return (
    <main className="groot-interface">
      <GrootOrb resetSignal={resetSignal} />

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

      <section className="gesture-panel" aria-label="Gesture input placeholder">
        <div className="gesture-copy">
          <span>MEDIAPIPE FOUNDATION</span>
          <strong>
            {gesturesEnabled ? "PLACEHOLDER ON" : "GESTURES STANDBY"}
          </strong>
          <small>CAMERA INACTIVE</small>
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
