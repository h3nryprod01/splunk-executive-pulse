"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  src: string;
  durationSec: number;
}

export default function AudioPlayer({ src, durationSec }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const a = audioRef.current!;
    const onTime = () => {
      setCurrent(a.currentTime);
      setProgress((a.currentTime / (a.duration || durationSec)) * 100);
    };
    const onEnd = () => setPlaying(false);
    a.addEventListener("timeupdate", onTime);
    a.addEventListener("ended", onEnd);
    return () => {
      a.removeEventListener("timeupdate", onTime);
      a.removeEventListener("ended", onEnd);
    };
  }, [durationSec]);

  const toggle = () => {
    const a = audioRef.current!;
    if (playing) a.pause();
    else a.play();
    setPlaying(!playing);
  };

  const fmt = (s: number) =>
    `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  // Decorative waveform — 60 bars
  const bars = Array.from({ length: 60 }, (_, i) => 10 + Math.sin(i * 0.7) * 8 + Math.random() * 14);

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <audio ref={audioRef} src={src} preload="metadata" />
      <div className="flex items-center gap-4">
        <button
          onClick={toggle}
          className="w-14 h-14 rounded-full bg-splunk hover:bg-splunk-dark transition-colors flex items-center justify-center text-bg shadow-lg"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M7 5l11 7-11 7V5z"/></svg>
          )}
        </button>

        <div className="flex-1 flex items-end gap-[3px] h-10">
          {bars.map((h, i) => {
            const active = (i / bars.length) * 100 <= progress;
            return (
              <div
                key={i}
                className={`w-[3px] rounded-full transition-colors ${active ? "bg-splunk" : "bg-border"}`}
                style={{ height: `${h}px` }}
              />
            );
          })}
        </div>

        <div className="font-mono text-sm text-dim min-w-[80px] text-right">
          {fmt(current)} / {fmt(durationSec)}
        </div>
      </div>
    </div>
  );
}
