export interface Event { id: string; source_event_id: string; magnitude: number | null; magnitude_type: string | null; place: string | null; latitude: number; longitude: number; depth_km: number | null; occurred_at: string; source_updated_at: string | null; event_type: string | null; source_status: string | null; event_url: string | null; data_source: { code: string; name: string } | null }
export interface EventPage { items: Event[]; limit: number; offset: number; total: number }
export interface Summary { total_events: number; events_with_magnitude: number; largest_magnitude: number | null; average_magnitude: number | null; magnitude_distribution: { below_2: number; from_2_to_below_4: number; from_4_to_below_5: number; above_or_equal_5: number } }
export interface Geographic { bounds: { south: number; north: number; west: number; east: number; crosses_antimeridian: boolean }; total_events: number; events_with_magnitude: number; events_without_magnitude: number; smallest_magnitude: number | null; largest_magnitude: number | null; average_magnitude: number | null }
export interface ScenarioInput { latitude: number; longitude: number; magnitude: number; depth_km: number; radius_km: number }
export interface ScenarioResult { scenario: ScenarioInput; historical_catalog: { events_within_radius: number; events_with_magnitude: number; events_without_magnitude: number; smallest_magnitude: number | null; largest_magnitude: number | null; average_magnitude: number | null; nearest_distance_km: number | null; farthest_distance_km: number | null; average_distance_km: number | null } }
export interface EarlyWarningTarget { name: string; latitude: number; longitude: number }
export interface EarlyWarningInput extends Omit<ScenarioInput, "radius_km"> {
	detection_delay_seconds: number;
	processing_delay_seconds: number;
	sensor_count: number;
	required_sensor_count: number;
	sensor_radius_km: number;
	p_wave_velocity_km_s: number;
	s_wave_velocity_km_s: number;
	targets: EarlyWarningTarget[];
}
export interface SimulatedSensor { id: string; latitude: number; longitude: number; epicentral_distance_km: number; hypocentral_distance_km: number; p_arrival_seconds: number; detected_seconds: number; processed_seconds: number }
export interface TargetWarningResult extends EarlyWarningTarget {
	epicentral_distance_km: number;
	hypocentral_distance_km: number;
	p_arrival_seconds: number;
	s_arrival_seconds: number;
	first_detection_seconds: number;
	alert_issuance_seconds: number;
	warning_lead_seconds: number;
	status: "potential_lead_time" | "no_useful_lead_time" | "shaking_before_alert";
}
export interface EarlyWarningResult {
	scenario: EarlyWarningInput;
	model: { name: string; earth_radius_km: number; p_wave_velocity_km_s: number; s_wave_velocity_km_s: number; detection_delay_seconds: number; processing_delay_seconds: number; required_sensor_count: number; travel_time_formula: string; sensor_distribution: string; alert_rule: string; limitations: string[] };
	first_detection_seconds: number;
	alert_issuance_seconds: number;
	sensors: SimulatedSensor[];
	targets: TargetWarningResult[];
}
