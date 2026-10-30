import type { EarlyWarningInput, EarlyWarningResult, Event, EventPage, Geographic, ScenarioInput, ScenarioResult, Summary } from "./types";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export class ApiError extends Error { constructor(message: string, readonly status?: number) { super(message); this.name = "ApiError"; } }
type Decimal = number | string;
export type EventQuery = { limit?: number; offset?: number; min_magnitude?: number; start_time?: string; end_time?: string };
type ApiEvent = Omit<Event, "magnitude" | "latitude" | "longitude" | "depth_km"> & { magnitude: Decimal | null; latitude: Decimal; longitude: Decimal; depth_km: Decimal | null };
type ApiSummary = Omit<Summary, "largest_magnitude" | "average_magnitude"> & { largest_magnitude: Decimal | null; average_magnitude: Decimal | null };
type ApiGeographic = Omit<Geographic, "bounds" | "smallest_magnitude" | "largest_magnitude" | "average_magnitude"> & { bounds: { south: Decimal; north: Decimal; west: Decimal; east: Decimal; crosses_antimeridian: boolean }; smallest_magnitude: Decimal | null; largest_magnitude: Decimal | null; average_magnitude: Decimal | null };
type ApiScenario = { scenario: Record<keyof ScenarioInput, Decimal>; historical_catalog: Record<"events_within_radius" | "events_with_magnitude" | "events_without_magnitude", number> & Record<"smallest_magnitude" | "largest_magnitude" | "average_magnitude" | "nearest_distance_km" | "farthest_distance_km" | "average_distance_km", Decimal | null> };

const numeric = (value: Decimal | null): number | null => value === null ? null : Number(value);
function requiredNumber(value: Decimal): number { const result = Number(value); if (!Number.isFinite(result)) throw new ApiError("The API returned an invalid numeric value."); return result; }
function errorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map(item => {
        if (typeof item !== "object" || item === null || !("msg" in item)) return "Invalid request";
        const message = String((item as { msg: unknown }).msg);
        const location = "loc" in item && Array.isArray((item as { loc: unknown }).loc)
          ? ((item as { loc: unknown[] }).loc).slice(1).join(".")
          : "";
        return location ? `${location}: ${message}` : message;
      }).join("; ");
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  try { response = await fetch(`${apiBaseUrl}/api/v1${path}`, { ...init, headers }); }
  catch { throw new ApiError("Unable to reach the ResQ API. Check that the backend is running and the API URL is configured."); }
  const text = await response.text(); let payload: unknown;
  if (text) { try { payload = JSON.parse(text); } catch { payload = text; } }
  if (!response.ok) throw new ApiError(errorMessage(payload, `Request failed (${response.status}).`), response.status);
  if (payload === undefined) throw new ApiError("The API returned an empty response.", response.status);
  if (typeof payload === "string") throw new ApiError("The API returned an invalid JSON response.", response.status);
  return payload as T;
}

function eventFromApi(event: ApiEvent): Event { return { ...event, magnitude: numeric(event.magnitude), latitude: requiredNumber(event.latitude), longitude: requiredNumber(event.longitude), depth_km: numeric(event.depth_km) }; }
function scenarioFromApi(result: ApiScenario): ScenarioResult { const h = result.historical_catalog; return { scenario: { latitude: requiredNumber(result.scenario.latitude), longitude: requiredNumber(result.scenario.longitude), magnitude: requiredNumber(result.scenario.magnitude), depth_km: requiredNumber(result.scenario.depth_km), radius_km: requiredNumber(result.scenario.radius_km) }, historical_catalog: { ...h, smallest_magnitude: numeric(h.smallest_magnitude), largest_magnitude: numeric(h.largest_magnitude), average_magnitude: numeric(h.average_magnitude), nearest_distance_km: numeric(h.nearest_distance_km), farthest_distance_km: numeric(h.farthest_distance_km), average_distance_km: numeric(h.average_distance_km) } }; }

export const api = {
  async summary(): Promise<Summary> { const value = await request<ApiSummary>("/analytics/summary"); return { ...value, largest_magnitude: numeric(value.largest_magnitude), average_magnitude: numeric(value.average_magnitude) }; },
  async events(params: EventQuery): Promise<EventPage> { const query = new URLSearchParams(); Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== "") query.set(key, String(value)); }); const value = await request<Omit<EventPage, "items"> & { items: ApiEvent[] }>(`/seismic-events?${query}`); return { ...value, items: value.items.map(eventFromApi) }; },
  async geographic(params: Record<string, number>): Promise<Geographic> { const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)])); const value = await request<ApiGeographic>(`/analytics/geographic?${query}`); return { ...value, bounds: { ...value.bounds, south: requiredNumber(value.bounds.south), north: requiredNumber(value.bounds.north), west: requiredNumber(value.bounds.west), east: requiredNumber(value.bounds.east) }, smallest_magnitude: numeric(value.smallest_magnitude), largest_magnitude: numeric(value.largest_magnitude), average_magnitude: numeric(value.average_magnitude) }; },
  async scenario(input: ScenarioInput): Promise<ScenarioResult> { return scenarioFromApi(await request<ApiScenario>("/scenarios/earthquake", { method: "POST", body: JSON.stringify(input) })); },
  async earlyWarning(input: EarlyWarningInput): Promise<EarlyWarningResult> { return request<EarlyWarningResult>("/scenarios/early-warning", { method: "POST", body: JSON.stringify(input) }); },
};
