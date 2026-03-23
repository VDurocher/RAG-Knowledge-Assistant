"use client";

import type { ChatSettings } from "@/lib/types";

interface SettingsPanelProps {
  settings: ChatSettings;
  onChange: (settings: ChatSettings) => void;
}

export function SettingsPanel({ settings, onChange }: SettingsPanelProps) {
  return (
    <div className="space-y-5">
      {/* Seuil de confiance */}
      <div>
        <div className="flex justify-between mb-2">
          <label className="text-xs text-[#a1a1aa]">Confidence threshold</label>
          <span className="text-xs font-mono text-[#7c3aed]">{settings.score_threshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0.1}
          max={0.9}
          step={0.05}
          value={settings.score_threshold}
          onChange={e => onChange({ ...settings, score_threshold: parseFloat(e.target.value) })}
          className="w-full h-1 rounded-full accent-[#7c3aed]"
        />
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-[#52525b]">Permissive</span>
          <span className="text-[10px] text-[#52525b]">Strict</span>
        </div>
      </div>

      {/* Nombre de résultats */}
      <div>
        <div className="flex justify-between mb-2">
          <label className="text-xs text-[#a1a1aa]">Results per query</label>
          <span className="text-xs font-mono text-[#7c3aed]">{settings.k}</span>
        </div>
        <input
          type="range"
          min={1}
          max={10}
          step={1}
          value={settings.k}
          onChange={e => onChange({ ...settings, k: parseInt(e.target.value) })}
          className="w-full h-1 rounded-full accent-[#7c3aed]"
        />
      </div>

      {/* Toggle fallback */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-[#a1a1aa]">General knowledge fallback</p>
          <p className="text-[10px] text-[#52525b] mt-0.5">Answer from LLM if nothing found</p>
        </div>
        <button
          onClick={() => onChange({ ...settings, fallback_enabled: !settings.fallback_enabled })}
          aria-label={settings.fallback_enabled ? "Disable fallback" : "Enable fallback"}
          className={`w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0 relative ${
            settings.fallback_enabled ? "bg-[#7c3aed]" : "bg-[#2d1f5e]"
          }`}
        >
          <span
            className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${
              settings.fallback_enabled ? "translate-x-4" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>
    </div>
  );
}
