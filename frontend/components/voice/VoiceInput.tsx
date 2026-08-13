"use client";

import { useEffect, useRef, useState } from "react";

interface VoiceInputProps {
  onTranscript?: (transcript: string) => void;
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

export default function VoiceInput({
  onTranscript,
}: VoiceInputProps) {
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [supported, setSupported] = useState(true);

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
    recognition.lang = "en-US";

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
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [onTranscript]);

  const toggleListening = () => {
    const recognition = recognitionRef.current;

    if (!recognition) {
      return;
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
      return;
    }

    setTranscript("");
    recognition.start();
    setIsListening(true);
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
        {isListening ? "Listening..." : "Voice ready"}
      </div>

      {transcript && (
        <div className="voice-input-transcript">
          {transcript}
        </div>
      )}
    </div>
  );
}
