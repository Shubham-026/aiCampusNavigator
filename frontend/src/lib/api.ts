export interface SearchMatch {
  place_id: string;
  name: string;
  category: string;
  department: string;
  floor: number;
  floor_name: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  matches: SearchMatch[];
}

export interface RouteMapNode {
  place_id: string;
  name: string;
  x: number;
  y: number;
  floor: number;
  floor_name: string;
}

export interface RouteResponse {
  algorithm: string;
  nodes: string[];
  map_nodes: RouteMapNode[];
  instructions: string[];
  total_distance_m: number;
  estimated_walking_time_seconds: number;
}

export interface HealthResponse {
  status: string;
}

export interface SignVerificationResponse {
  destination_id: string;
  matched: boolean;
  score: number;
  matched_label: string | null;
  extracted_text: string;
}

const API_BASE = (process.env.NEXT_PUBLIC_CAMPUS_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function readResponse<T>(response: Response): Promise<T> {
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String(payload.detail)
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return payload as T;
}

export async function searchPlaces(query: string, signal?: AbortSignal): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, limit: "7", score_threshold: "35" });
  const response = await fetch(`${API_BASE}/search?${params}`, { signal, cache: "no-store" });
  return readResponse<SearchResponse>(response);
}

export async function checkApi(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`, { signal, cache: "no-store" });
  return readResponse<HealthResponse>(response);
}

export async function fetchRoute(
  startId: string,
  destinationId: string,
  signal?: AbortSignal,
): Promise<RouteResponse> {
  const response = await fetch(`${API_BASE}/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start_id: startId, destination_id: destinationId }),
    cache: "no-store",
    signal,
  });
  return readResponse<RouteResponse>(response);
}

export async function verifyRoomSign(
  image: File,
  destination: Pick<SearchMatch, "place_id" | "name">,
): Promise<SignVerificationResponse> {
  const formData = new FormData();
  formData.append("image", image);
  formData.append("destination_id", destination.place_id);
  formData.append("destination_name", destination.name);
  const response = await fetch(`${API_BASE}/verify-sign`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  return readResponse<SignVerificationResponse>(response);
}
