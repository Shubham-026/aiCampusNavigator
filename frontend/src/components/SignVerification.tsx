"use client";

import { useEffect, useRef, useState } from "react";
import { BadgeCheck, Camera, Check, ImagePlus, LoaderCircle, RotateCcw, Upload, X } from "lucide-react";
import Image from "next/image";

import { verifyRoomSign, type SearchMatch, type SignVerificationResponse } from "@/lib/api";

interface SignVerificationProps {
  destination: SearchMatch | null;
}

export function SignVerification({ destination }: SignVerificationProps) {
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState<SignVerificationResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  function chooseImage(file?: File) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Choose a JPEG, PNG, or WebP image.");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setError("The image must be 8 MB or smaller.");
      return;
    }
    setImage(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError("");
  }

  async function submitImage() {
    if (!image || !destination) return;
    setLoading(true);
    setError("");
    try {
      setResult(await verifyRoomSign(image, destination));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to verify this sign.");
    } finally {
      setLoading(false);
    }
  }

  function clearImage() {
    setImage(null);
    setPreviewUrl("");
    setResult(null);
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section className="verify-panel" aria-labelledby="verify-title">
      <div className="section-heading section-heading--compact">
        <div><span className="eyebrow">ARRIVAL CHECK</span><h2 id="verify-title">Verify room sign</h2></div>
        <span className="optional-tag">OPTIONAL</span>
      </div>
      <p className="verify-copy">Compare a room sign with your selected destination.</p>
      {!image ? (
        <button
          className={`upload-zone ${dragging ? "upload-zone--dragging" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => { event.preventDefault(); setDragging(false); chooseImage(event.dataTransfer.files[0]); }}
          type="button"
        >
          <span className="upload-icon"><ImagePlus size={20} /></span>
          <span className="upload-main">Drop a sign photo or browse</span>
          <span className="upload-sub">JPEG, PNG or WebP · up to 8 MB</span>
          <span className="upload-actions"><Upload size={14} /> Browse files <span /> <Camera size={14} /> Use camera</span>
        </button>
      ) : (
        <div className="image-review">
          <Image alt="Selected room sign preview" className="image-preview" height={46} src={previewUrl} unoptimized width={54} />
          <div className="image-review-copy">
            <strong>{image.name}</strong><small>{(image.size / 1024).toFixed(0)} KB · Ready to verify</small>
            <div className="image-review-actions">
              <button className="text-action" onClick={() => inputRef.current?.click()} type="button"><RotateCcw size={13} /> Replace</button>
              <button className="text-action text-action--muted" onClick={clearImage} type="button"><X size={13} /> Remove</button>
            </div>
          </div>
          <button aria-label="Remove image" className="icon-button image-remove" onClick={clearImage} type="button"><X size={15} /></button>
        </div>
      )}
      <input accept="image/jpeg,image/png,image/webp" capture="environment" className="visually-hidden" onChange={(event) => chooseImage(event.target.files?.[0])} ref={inputRef} type="file" />
      {error && <div className="verify-message verify-message--error" role="alert"><X size={15} />{error}</div>}
      {result && (
        <div className={`verify-result ${result.matched ? "verify-result--success" : "verify-result--miss"}`} role="status">
          {result.matched ? <BadgeCheck size={18} /> : <X size={18} />}
          <div><strong>{result.matched ? "Destination confirmed" : "Room not confirmed"}</strong><span>{(result.matched_label ?? result.extracted_text) || "No readable sign text"} · {Math.round(result.score)}% match</span></div>
          {result.matched && <Check className="verify-check" size={17} />}
        </div>
      )}
      <button className="verify-button" disabled={!image || !destination || loading} onClick={submitImage} type="button">
        {loading ? <LoaderCircle className="spin" size={16} /> : <BadgeCheck size={16} />}
        {loading ? "Checking sign…" : destination ? `Verify ${destination.name}` : "Choose a destination first"}
      </button>
      {!destination && <small className="verify-footnote">Select a destination to enable arrival verification.</small>}
    </section>
  );
}
