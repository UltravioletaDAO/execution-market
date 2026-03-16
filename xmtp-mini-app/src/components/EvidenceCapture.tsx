import { useState, useRef } from "react";
import type { EvidenceRequirement } from "../services/types";

interface Props {
  requirements: EvidenceRequirement[];
  onCapture: (type: string, data: File | string | GeolocationPosition) => void;
}

export function EvidenceCapture({ requirements, onCapture }: Props) {
  const [gpsLoading, setGpsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const capturePhoto = () => {
    fileInputRef.current?.click();
  };

  const captureGPS = () => {
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onCapture("gps", pos);
        setGpsLoading(false);
      },
      (err) => {
        console.error("GPS error:", err);
        setGpsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  return (
    <div className="space-y-3">
      {requirements.map((req) => (
        <div key={req.type} className="p-3 border border-white/10 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-white text-sm font-medium">{req.label}</span>
            {!req.required && <span className="text-white/30 text-xs">Opcional</span>}
          </div>

          {req.type === "photo" && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onCapture("photo", file);
                }}
              />
              <button
                onClick={capturePhoto}
                className="w-full py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white/60 hover:bg-white/10"
              >
                Tomar Foto
              </button>
            </>
          )}

          {req.type === "gps" && (
            <button
              onClick={captureGPS}
              disabled={gpsLoading}
              className="w-full py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white/60 hover:bg-white/10 disabled:opacity-50"
            >
              {gpsLoading ? "Obteniendo ubicacion..." : "Capturar GPS"}
            </button>
          )}

          {req.type === "text" && (
            <textarea
              placeholder="Escribe aqui..."
              rows={3}
              className="w-full bg-white/5 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 border border-white/10 focus:border-white/30 outline-none resize-none"
              onChange={(e) => onCapture("text", e.target.value)}
            />
          )}
        </div>
      ))}
    </div>
  );
}
