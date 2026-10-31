import { FormEvent, useEffect, useState } from "react";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { api } from "./api";
import "./early-warning.css";
import type { EarlyWarningInput, EarlyWarningResult, EarlyWarningTarget, ScenarioInput, SimulatedSensor } from "./types";

const exampleTargets: EarlyWarningTarget[] = [
  { name: "Kabul (example)", latitude: 34.5553, longitude: 69.2075 },
  { name: "Kandahar (example)", latitude: 31.6289, longitude: 65.7372 },
  { name: "Herat (example)", latitude: 34.3529, longitude: 62.204 },
];
const initialConfig = {
  detection_delay_seconds: 0.8,
  processing_delay_seconds: 0.5,
  sensor_count: 8,
  required_sensor_count: 2,
  sensor_radius_km: 250,
  p_wave_velocity_km_s: 6,
  s_wave_velocity_km_s: 3.5,
  targets: exampleTargets,
};
const fmt = (value: number, digits = 1) => Number.isFinite(value) ? value.toFixed(digits) : "—";
const statusText = {
  potential_lead_time: "Potential lead time",
  no_useful_lead_time: "No useful lead time",
  shaking_before_alert: "Shaking expected before alert issuance",
};

function Viewport({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => { map.setView(center, map.getZoom()); }, [center, map]);
  return null;
}

function MapPicker({ onPick }: { onPick: (latitude: number, longitude: number) => void }) {
  useMapEvents({ click: event => onPick(event.latlng.lat, event.latlng.lng) });
  return null;
}

function waveRadiusKm(time: number, velocity: number, depth: number, earthRadiusKm: number) {
  const travelDistance = velocity * time;
  const surfaceRadius = travelDistance <= depth ? 0 : Math.sqrt(travelDistance ** 2 - depth ** 2);
  return Math.min(surfaceRadius, Math.PI * earthRadiusKm);
}

function sensorState(sensor: SimulatedSensor, time: number) {
  if (time < sensor.detected_seconds) return "Waiting for P-wave";
  if (time < sensor.processed_seconds) return "P-wave detected";
  return "Detection processed";
}

export function EarlyWarningPanel({ scenario, onScenarioChange }: { scenario: ScenarioInput; onScenarioChange: (value: ScenarioInput) => void }) {
  const [config, setConfig] = useState(initialConfig);
  const [result, setResult] = useState<EarlyWarningResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [simulationTime, setSimulationTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [pickMode, setPickMode] = useState<"epicenter" | "target">("epicenter");
  const [selectedTarget, setSelectedTarget] = useState(0);

  const maximumTime = result
    ? Math.max(...result.targets.map(target => target.s_arrival_seconds), ...result.sensors.map(sensor => sensor.processed_seconds), result.alert_issuance_seconds) + 5
    : 0;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setSimulationTime(current => {
        const next = current + 0.1;
        if (next >= maximumTime) {
          setPlaying(false);
          return maximumTime;
        }
        return next;
      });
    }, 100);
    return () => window.clearInterval(timer);
  }, [playing, maximumTime]);

  useEffect(() => {
    setResult(undefined);
    setPlaying(false);
    setSimulationTime(0);
  }, [scenario.latitude, scenario.longitude, scenario.magnitude, scenario.depth_km]);

  const updateConfig = (key: keyof Omit<typeof config, "targets">, value: number) => {
    setConfig(current => ({ ...current, [key]: value }));
    setResult(undefined);
    setPlaying(false);
    setSimulationTime(0);
    setError("");
  };
  const updateTarget = (index: number, field: keyof EarlyWarningTarget, value: string) => {
    setConfig(current => ({
      ...current,
      targets: current.targets.map((target, targetIndex) => targetIndex === index
        ? { ...target, [field]: field === "name" ? value : Number(value) }
        : target),
    }));
    setResult(undefined);
    setPlaying(false);
    setSimulationTime(0);
    setError("");
  };
  const pickLocation = (latitude: number, longitude: number) => {
    setResult(undefined);
    setPlaying(false);
    setSimulationTime(0);
    if (pickMode === "epicenter") {
      onScenarioChange({ ...scenario, latitude: Number(latitude.toFixed(4)), longitude: Number(longitude.toFixed(4)) });
    } else {
      setConfig(current => ({
        ...current,
        targets: current.targets.map((target, index) => index === selectedTarget
          ? { ...target, latitude: Number(latitude.toFixed(4)), longitude: Number(longitude.toFixed(4)) }
          : target),
      }));
    }
  };
  const runSimulation = async (event: FormEvent) => {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setPlaying(false);
    setError("");
    try {
      const simulation = await api.earlyWarning({
        latitude: scenario.latitude,
        longitude: scenario.longitude,
        magnitude: scenario.magnitude,
        depth_km: scenario.depth_km,
        ...config,
      });
      setResult(simulation);
      setSimulationTime(0);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Simulation request failed.");
    } finally {
      setLoading(false);
    }
  };

  const processedCount = result?.sensors.filter(sensor => simulationTime >= sensor.processed_seconds).length ?? 0;
  const detectedCount = result?.sensors.filter(sensor => simulationTime >= sensor.detected_seconds).length ?? 0;
  const alertIssued = !!result && simulationTime >= result.alert_issuance_seconds;
  const pRadius = result ? waveRadiusKm(simulationTime, result.model.p_wave_velocity_km_s, scenario.depth_km, result.model.earth_radius_km) : 0;
  const sRadius = result ? waveRadiusKm(simulationTime, result.model.s_wave_velocity_km_s, scenario.depth_km, result.model.earth_radius_km) : 0;
  const maximumSurfaceRadius = result ? Math.PI * result.model.earth_radius_km : 0;

  return <section className="warning-simulation" aria-labelledby="warning-title">
    <div className="warning-heading">
      <div><p className="eyebrow">Modeled propagation</p><h3 id="warning-title">Early-warning research simulation</h3></div>
      <strong className="research-banner">Research Simulation — Not a Real-Time Warning Service</strong>
    </div>
    <p className="warning-copy">Configure an idealized synthetic sensor network and target locations. These are deterministic model outputs, not station readings or safety guarantees.</p>
    <form className="warning-form" onSubmit={runSimulation}>
      <div className="warning-controls">
        <label>Detection delay (s)<input type="number" min="0" max="60" step="0.1" value={config.detection_delay_seconds} onChange={event => updateConfig("detection_delay_seconds", Number(event.target.value))} required /></label>
        <label>Processing delay (s)<input type="number" min="0" max="60" step="0.1" value={config.processing_delay_seconds} onChange={event => updateConfig("processing_delay_seconds", Number(event.target.value))} required /></label>
        <label>Synthetic sensors<input type="number" min="1" max="20" step="1" value={config.sensor_count} onChange={event => updateConfig("sensor_count", Number(event.target.value))} required /></label>
        <label>Quorum required<input type="number" min="1" max="20" step="1" value={config.required_sensor_count} onChange={event => updateConfig("required_sensor_count", Number(event.target.value))} required /></label>
        <label>Network radius (km)<input type="number" min="1" max="1000" step="1" value={config.sensor_radius_km} onChange={event => updateConfig("sensor_radius_km", Number(event.target.value))} required /></label>
        <label>P-wave velocity (km/s)<input type="number" min="3" max="8" step="0.1" value={config.p_wave_velocity_km_s} onChange={event => updateConfig("p_wave_velocity_km_s", Number(event.target.value))} required /></label>
        <label>S-wave velocity (km/s)<input type="number" min="1.5" max="5" step="0.1" value={config.s_wave_velocity_km_s} onChange={event => updateConfig("s_wave_velocity_km_s", Number(event.target.value))} required /></label>
      </div>
      <div className="target-editor">
        <div className="target-editor-heading"><div><strong>Target locations</strong><small>Example city coordinates; editable and selectable on map</small></div><button type="button" className="quiet-button" disabled={config.targets.length >= 8} onClick={() => { setConfig(current => ({ ...current, targets: [...current.targets, { name: `Target ${current.targets.length + 1}`, latitude: scenario.latitude, longitude: scenario.longitude }] })); setResult(undefined); setPlaying(false); setSimulationTime(0); setSelectedTarget(config.targets.length); setPickMode("target"); }}>Add target</button></div>
        {config.targets.map((target, index) => <div className="target-fields" key={index}>
          <label>Name<input maxLength={80} value={target.name} onChange={event => updateTarget(index, "name", event.target.value)} required /></label>
          <label>Latitude<input type="number" min="-90" max="90" step="any" value={target.latitude} onChange={event => updateTarget(index, "latitude", event.target.value)} required /></label>
          <label>Longitude<input type="number" min="-180" max="180" step="any" value={target.longitude} onChange={event => updateTarget(index, "longitude", event.target.value)} required /></label>
          <button type="button" className="icon-button" aria-label={`Remove ${target.name || `target ${index + 1}`}`} title="Remove target" disabled={config.targets.length <= 1} onClick={() => { setConfig(current => ({ ...current, targets: current.targets.filter((_, targetIndex) => targetIndex !== index) })); setResult(undefined); setPlaying(false); setSimulationTime(0); setSelectedTarget(current => Math.max(0, current >= index ? current - 1 : current)); }}>×</button>
        </div>)}
      </div>
      <div className="map-pick-controls" role="group" aria-label="Map selection mode"><span>Map click sets:</span><button type="button" aria-pressed={pickMode === "epicenter"} onClick={() => setPickMode("epicenter")}>Epicenter</button><button type="button" aria-pressed={pickMode === "target"} onClick={() => setPickMode("target")}>Target</button>{pickMode === "target" && <select aria-label="Target to set on map" value={selectedTarget} onChange={event => setSelectedTarget(Number(event.target.value))}>{config.targets.map((target, index) => <option key={index} value={index}>{target.name || `Target ${index + 1}`}</option>)}</select>}</div>
      <MapContainer center={[scenario.latitude, scenario.longitude]} zoom={5} scrollWheelZoom className="warning-map">
        <Viewport center={[scenario.latitude, scenario.longitude]} />
        <MapPicker onPick={pickLocation} />
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {result && pRadius > 0 && pRadius < maximumSurfaceRadius && <Circle center={[scenario.latitude, scenario.longitude]} radius={pRadius * 1000} pathOptions={{ color: "#45d5e6", fillOpacity: 0.025, weight: 2, dashArray: "7 7" }} />}
        {result && sRadius > 0 && sRadius < maximumSurfaceRadius && <Circle center={[scenario.latitude, scenario.longitude]} radius={sRadius * 1000} pathOptions={{ color: "#ff9b67", fillOpacity: 0.02, weight: 2, dashArray: "4 8" }} />}
        <CircleMarker center={[scenario.latitude, scenario.longitude]} radius={9} pathOptions={{ color: "#fff0c1", fillColor: "#ff745e", fillOpacity: 1, weight: 2 }}><Popup>Hypothetical earthquake epicenter</Popup></CircleMarker>
        {config.targets.map((target, index) => {
          const targetResult = result?.targets.find(item => item.name === target.name);
          const noLead = targetResult && targetResult.status !== "potential_lead_time";
          return <CircleMarker key={`target-${index}`} center={[target.latitude, target.longitude]} radius={7} pathOptions={{ color: "#fff", fillColor: noLead ? "#ef806b" : "#ffcf70", fillOpacity: 1, weight: 2 }}><Popup>{target.name || `Target ${index + 1}`}<br />Example target location, not a warning recipient{targetResult && <><br />{statusText[targetResult.status]}<br />Modeled lead: {fmt(targetResult.warning_lead_seconds)} s</>}</Popup></CircleMarker>;
        })}
        {result?.sensors.map(sensor => <CircleMarker key={sensor.id} center={[sensor.latitude, sensor.longitude]} radius={5} pathOptions={{ color: "#07182c", fillColor: simulationTime >= sensor.processed_seconds ? "#79e2b0" : simulationTime >= sensor.detected_seconds ? "#f6d365" : "#b0bdcc", fillOpacity: 1, weight: 1 }}><Popup><strong>Simulated sensor {sensor.id}</strong><br />{sensorState(sensor, simulationTime)}<br />Modeled P arrival: {fmt(sensor.p_arrival_seconds)} s<br />Detection: {fmt(sensor.detected_seconds)} s · Processed: {fmt(sensor.processed_seconds)} s</Popup></CircleMarker>)}
      </MapContainer>
      <div className="map-legend" aria-label="Map legend"><span><i className="legend-epicenter" />Hypothetical epicenter</span><span><i className="legend-target" />Target with potential lead</span><span><i className="legend-no-lead" />Zero/negative lead</span><span><i className="legend-waiting" />Sensor waiting</span><span><i className="legend-detected" />P detected</span><span><i className="legend-sensor" />Detection processed</span><span><i className="legend-p" />P-wavefront</span><span><i className="legend-s" />S-wavefront</span></div>
      {result && (pRadius >= maximumSurfaceRadius || sRadius >= maximumSurfaceRadius) && <p className="wavefront-limit" role="status">A modeled wavefront has reached the antipodal surface limit; no distinct farther surface front is drawn.</p>}
      <div className="simulation-toolbar">
        <div className="playback-controls"><button type="button" title="Play simulation" aria-label="Play simulation" disabled={!result || playing || simulationTime >= maximumTime} onClick={() => setPlaying(true)}>▶</button><button type="button" title="Pause simulation" aria-label="Pause simulation" disabled={!playing} onClick={() => setPlaying(false)}>Ⅱ</button><button type="button" title="Reset simulation clock" aria-label="Reset simulation clock" disabled={!result} onClick={() => { setPlaying(false); setSimulationTime(0); }}>↺</button></div>
        <div className="clock-readout"><span>SIMULATION TIME</span><strong>{fmt(simulationTime, 1)} s</strong></div>
        <div className="alert-readout"><span>MODELED ALERT</span><strong className={alertIssued ? "issued" : "pending"}>{alertIssued ? "Issued" : "Not yet issued"}</strong><small>{result ? `at ${fmt(result.alert_issuance_seconds)} s` : "Run simulation to calculate"}</small></div>
        <button type="submit" disabled={loading}>{loading ? "Calculating…" : result ? "Run again" : "Run simulation"}</button>
      </div>
    </form>
    {error && <div className="state error" role="alert">{error}</div>}
    {result && <>
      <div className="sensor-summary" aria-live="polite"><span><i className="legend-sensor" />{result.sensors.length} synthetic sensors</span><span>{detectedCount} detected P</span><span>{processedCount} processed</span><span>Quorum {result.model.required_sensor_count}/{result.sensors.length}</span></div>
      <div className="warning-table-wrap"><table className="warning-table"><thead><tr><th>Target</th><th>Distance</th><th>P arrival</th><th>S arrival</th><th>First detection</th><th>Alert time</th><th>Lead time</th><th>Time to S</th><th>Status</th></tr></thead><tbody>{result.targets.map(target => {
        const remaining = target.s_arrival_seconds - simulationTime;
        const noLead = target.status !== "potential_lead_time";
        return <tr key={target.name} className={noLead ? "no-lead-row" : ""}><th scope="row">{target.name}</th><td>{fmt(target.epicentral_distance_km)} km</td><td>{fmt(target.p_arrival_seconds)} s</td><td>{fmt(target.s_arrival_seconds)} s</td><td>{fmt(target.first_detection_seconds)} s</td><td>{fmt(target.alert_issuance_seconds)} s</td><td className={noLead ? "negative-lead" : "positive-lead"}>{target.warning_lead_seconds > 0 ? "+" : ""}{fmt(target.warning_lead_seconds)} s</td><td>{remaining > 0 ? `${fmt(remaining)} s` : "S arrival modeled"}</td><td><span className={`warning-status ${target.status}`}>{statusText[target.status]}</span></td></tr>;
      })}</tbody></table></div>
      <details className="model-notes"><summary>Model assumptions and limitations</summary><p>{result.model.travel_time_formula} Velocities: P {fmt(result.model.p_wave_velocity_km_s)} km/s; S {fmt(result.model.s_wave_velocity_km_s)} km/s.</p><p>{result.model.sensor_distribution} {result.model.alert_rule}</p><ul>{result.model.limitations.map(limitation => <li key={limitation}>{limitation}</li>)}</ul><p>A negative lead time means the model places S-wave arrival before alert issuance; it does not mean a warning could arrive before shaking.</p></details>
    </>}
  </section>;
}