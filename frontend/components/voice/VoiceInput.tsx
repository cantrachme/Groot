"use client";

import { useEffect, useRef, useState } from "react";

interface VoiceInputProps {
  onTranscript?: (transcript: string) => void;
  onListeningChange?: (listening: boolean) => void;
  audioLevelRef?: React.MutableRefObject<number>;
  wakeSuspended?: boolean;
}

interface SpeechRecognitionEventLike extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEventLike extends Event {
  error: string;
}

interface SpeechRecognitionLike extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult:
    | ((event: SpeechRecognitionEventLike) => void)
    | null;
  onerror:
    | ((event: SpeechRecognitionErrorEventLike) => void)
    | null;
  onend: (() => void) | null;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionLike;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const CLAP_THRESHOLD = 0.16;
const CLAP_RISE_THRESHOLD = 0.055;
const DOUBLE_CLAP_WINDOW = 750;
const CLAP_COOLDOWN = 900;

export default function VoiceInput({
  onTranscript,
  onListeningChange,
  audioLevelRef,
  wakeSuspended = false,
}: VoiceInputProps) {
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const listeningRef = useRef(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const previousLevelRef = useRef(0);
  const lastClapRef = useRef(0);
  const lastWakeRef = useRef(0);

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [supported, setSupported] = useState(true);
  const [wakeReady, setWakeReady] = useState(false);

  const setListening = (value: boolean) => {
    listeningRef.current = value;
    setIsListening(value);
    onListeningChange?.(value);
  };

  const startListening = () => {
    const recognition = recognitionRef.current;

    if (!recognition || listeningRef.current) {
      return;
    }

    try {
      setTranscript("");
      recognition.start();
      setListening(true);
    } catch {
      setListening(false);
    }
  };

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-GB";

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0]?.transcript ?? "";

        if (result.isFinal) {
          finalTranscript += text;
        } else {
          interimTranscript += text;
        }
      }

      const currentTranscript =
        finalTranscript || interimTranscript;

      setTranscript(currentTranscript);

      if (finalTranscript.trim()) {
        onTranscript?.(finalTranscript.trim());
      }
    };

    recognition.onerror = () => {
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
      recognitionRef.current = null;
      setListening(false);
    };
  }, [onTranscript]);

  useEffect(() => {
    let cancelled = false;

    const startWakeDetector = async () => {
      try {
        const stream =
          await navigator.mediaDevices.getUserMedia({
            audio: true,
          });

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;

        const AudioContextConstructor =
          window.AudioContext ||
          (
            window as typeof window & {
              webkitAudioContext?: typeof AudioContext;
            }
          ).webkitAudioContext;

        if (!AudioContextConstructor) {
          return;
        }

        const audioContext = new AudioContextConstructor();

        if (audioContext.state === "suspended") {
          await audioContext.resume();
        }

        const source =
          audioContext.createMediaStreamSource(stream);

        const analyser = audioContext.createAnalyser();

        analyser.fftSize = 512;
        analyser.smoothingTimeConstant = 0.18;

        source.connect(analyser);

        audioContextRef.current = audioContext;
        analyserRef.current = analyser;

        setWakeReady(true);

        const data = new Uint8Array(
          analyser.fftSize,
        );

        const processAudio = () => {
          if (cancelled) {
            return;
          }

          analyser.getByteTimeDomainData(data);

          let sum = 0;

          for (let i = 0; i < data.length; i++) {
            const normalized =
              (data[i] - 128) / 128;

            sum += normalized * normalized;
          }

          const rms = Math.sqrt(
            sum / data.length,
          );

          const previous =
            previousLevelRef.current;

          const rise = rms - previous;

          previousLevelRef.current = rms;

          const normalizedLevel = Math.min(
            1,
            rms * 5,
          );

          if (audioLevelRef) {
            audioLevelRef.current =
              normalizedLevel;
          }

          const now = performance.now();

          const clapDetected =
            !wakeSuspended &&
            !listeningRef.current &&
            rms > CLAP_THRESHOLD &&
            rise > CLAP_RISE_THRESHOLD &&
            now - lastClapRef.current >
              CLAP_COOLDOWN;

          if (clapDetected) {
            const previousClap = lastClapRef.current;

            lastClapRef.current = now;

            if (
              previousClap > 0 &&
              now - previousClap <= DOUBLE_CLAP_WINDOW &&
              now - lastWakeRef.current > CLAP_COOLDOWN
            ) {
              lastWakeRef.current = now;
              startListening();
            }
          }

          animationFrameRef.current =
            requestAnimationFrame(processAudio);
        };

        animationFrameRef.current =
          requestAnimationFrame(processAudio);
      } catch (error) {
        console.warn(
          "GROOT wake microphone unavailable:",
          error,
        );
      }
    };

    void startWakeDetector();

    return () => {
      cancelled = true;

      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(
          animationFrameRef.current,
        );
      }

      streamRef.current
        ?.getTracks()
        .forEach((track) => track.stop());

      streamRef.current = null;

      analyserRef.current = null;

      if (audioContextRef.current) {
        void audioContextRef.current.close();
      }

      audioContextRef.current = null;

      if (audioLevelRef) {
        audioLevelRef.current = 0;
      }
    };
  }, [audioLevelRef, wakeSuspended]);

  const toggleListening = () => {
    const recognition = recognitionRef.current;

    if (!recognition) {
      return;
    }

    if (listeningRef.current) {
      recognition.stop();
      setListening(false);
      return;
    }

    startListening();
  };

  if (!supported) {
    return (
      <div className="voice-input voice-input-disabled">
        Voice input is not supported in this browser.
      </div>
    );
  }

  return (
    <div className="voice-input">
      <button
        type="button"
        onClick={toggleListening}
        aria-label={
          isListening
            ? "Stop voice input"
            : "Start voice input"
        }
        aria-pressed={isListening}
        className={`voice-input-button ${
          isListening ? "is-listening" : ""
        }`}
      >
        {isListening ? "■" : "●"}
      </button>

      <div className="voice-input-status">
        {isListening
          ? "Listening..."
          : wakeReady
            ? "Double clap to wake"
            : "Voice ready"}
      </div>

      {transcript && (
        <div className="voice-input-transcript">
          {transcript}
        </div>
      )}
    </div>
  );
}
