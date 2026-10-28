"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, LoaderCircle, MapPin, Search } from "lucide-react";

import { searchPlaces, type SearchMatch } from "@/lib/api";

interface PlacePickerProps {
  label: string;
  value: SearchMatch | null;
  placeholder: string;
  onSelect: (place: SearchMatch) => void;
  compact?: boolean;
}

export function PlacePicker({
  label,
  value,
  placeholder,
  onSelect,
  compact = false,
}: PlacePickerProps) {
  const [query, setQuery] = useState(value?.name ?? "");
  const [results, setResults] = useState<SearchMatch[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setQuery(value?.name ?? "");
  }, [value]);

  useEffect(() => {
    const trimmed = query.trim();
    if (!open || trimmed.length < 2 || trimmed === value?.name) {
      setResults([]);
      setError("");
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const response = await searchPlaces(trimmed, controller.signal);
        setResults(response.matches);
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setResults([]);
          setError(requestError instanceof Error ? requestError.message : "Search is unavailable.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 240);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, open, value?.name]);

  useEffect(() => {
    function closeOnOutsideClick(event: PointerEvent) {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => document.removeEventListener("pointerdown", closeOnOutsideClick);
  }, []);

  function selectPlace(place: SearchMatch) {
    onSelect(place);
    setQuery(place.name);
    setResults([]);
    setOpen(false);
    setError("");
  }

  return (
    <div className={`place-picker ${compact ? "place-picker--compact" : ""}`} ref={rootRef}>
      <label className="field-label" htmlFor={`place-${label.toLowerCase().replaceAll(" ", "-")}`}>
        {label}
      </label>
      <div className={`picker-input-wrap ${open ? "picker-input-wrap--open" : ""}`}>
        <MapPin aria-hidden="true" className="picker-pin" size={17} />
        <input
          autoComplete="off"
          id={`place-${label.toLowerCase().replaceAll(" ", "-")}`}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Escape") setOpen(false);
            if (event.key === "ArrowDown" && results.length) {
              event.preventDefault();
              rootRef.current?.querySelector<HTMLButtonElement>(".suggestion-option")?.focus();
            }
          }}
          placeholder={placeholder}
          role="combobox"
          aria-autocomplete="list"
          aria-controls={`suggestions-${label.toLowerCase().replaceAll(" ", "-")}`}
          aria-expanded={open && (results.length > 0 || loading || Boolean(error))}
          value={query}
        />
        {loading ? <LoaderCircle aria-label="Searching" className="spin" size={16} /> : <ChevronDown aria-hidden="true" className="picker-chevron" size={15} />}
        {open && (results.length > 0 || loading || error) && (
          <div className="suggestion-menu" id={`suggestions-${label.toLowerCase().replaceAll(" ", "-")}`} role="listbox">
            {loading && <div className="suggestion-note">Searching campus places…</div>}
            {error && <div className="suggestion-note suggestion-note--error">{error}</div>}
            {!loading && results.map((place) => (
              <button
                className="suggestion-option"
                key={place.place_id}
                onClick={() => selectPlace(place)}
                onPointerDown={(event) => event.preventDefault()}
                onKeyDown={(event) => {
                  if (event.key === "Escape") setOpen(false);
                }}
                role="option"
                aria-selected={value?.place_id === place.place_id}
                type="button"
              >
                <span className="suggestion-icon"><Search aria-hidden="true" size={15} /></span>
                <span className="suggestion-copy">
                  <strong>{place.name}</strong>
                  <small>{place.department || place.category} · {place.floor_name}</small>
                </span>
                <span className="suggestion-score">{Math.round(place.score)}%</span>
                {value?.place_id === place.place_id && <Check aria-label="Selected" size={14} />}
              </button>
            ))}
            {!loading && !error && !results.length && query.trim().length >= 2 && (
              <div className="suggestion-note">No places found. Try a room number or nickname.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
