"""Deterministic idealized direct-wave and synthetic-sensor calculations.

Coordinates are WGS 84 degrees and distances are kilometers. Spherical surface
distance uses haversine; hypocentral distance is sqrt(surface_distance^2 +
depth^2), a local right-triangle approximation rather than a geocentric chord.
Direct P/S travel time is hypocentral_distance / velocity. The constant
velocities, golden-angle sensor pattern, and quorum alert rule are illustrative
assumptions, not an operational EEW model.
"""

from math import asin, atan2, cos, radians, sin, sqrt

from app.schemas.early_warning import (
    EarlyWarningSimulationRequest,
    EarlyWarningSimulationResult,
    SimulatedSensor,
    SimulationModelMetadata,
    TargetWarningResult,
)

EARTH_RADIUS_KM = 6371.0
GOLDEN_ANGLE_RADIANS = 2.399963229728653


def great_circle_distance_km(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    """Return spherical surface distance using the haversine equation."""
    lat_a, lat_b = radians(latitude_a), radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = radians(longitude_b - longitude_a)
    hav = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, hav)))


def _destination_point(
    latitude: float, longitude: float, distance_km: float, bearing_radians: float
) -> tuple[float, float]:
    angular_distance = distance_km / EARTH_RADIUS_KM
    lat_1, lon_1 = radians(latitude), radians(longitude)
    lat_2 = asin(
        sin(lat_1) * cos(angular_distance)
        + cos(lat_1) * sin(angular_distance) * cos(bearing_radians)
    )
    lon_2 = lon_1 + atan2(
        sin(bearing_radians) * sin(angular_distance) * cos(lat_1),
        cos(angular_distance) - sin(lat_1) * sin(lat_2),
    )
    longitude_degrees = (lon_2 * 180 / 3.141592653589793 + 540) % 360 - 180
    return lat_2 * 180 / 3.141592653589793, longitude_degrees


def warning_status(lead_seconds: float) -> str:
    if abs(lead_seconds) <= 1e-9:
        return "no_useful_lead_time"
    if lead_seconds > 0:
        return "potential_lead_time"
    return "shaking_before_alert"


def simulate_early_warning(
    scenario: EarlyWarningSimulationRequest,
) -> EarlyWarningSimulationResult:
    """Calculate an idealized wavefront and synthetic sensor network timeline."""
    sensors: list[SimulatedSensor] = []
    for index in range(scenario.sensor_count):
        fraction = (index + 1) / scenario.sensor_count
        radius = scenario.sensor_radius_km * sqrt(fraction)
        bearing = index * GOLDEN_ANGLE_RADIANS
        sensor_latitude, sensor_longitude = _destination_point(
            scenario.latitude, scenario.longitude, radius, bearing
        )
        epicentral_distance = great_circle_distance_km(
            scenario.latitude,
            scenario.longitude,
            sensor_latitude,
            sensor_longitude,
        )
        hypocentral_distance = sqrt(epicentral_distance**2 + scenario.depth_km**2)
        p_arrival = hypocentral_distance / scenario.p_wave_velocity_km_s
        detected = p_arrival + scenario.detection_delay_seconds
        processed = detected + scenario.processing_delay_seconds
        sensors.append(
            SimulatedSensor(
                id=f"SYN-{index + 1:02d}",
                latitude=sensor_latitude,
                longitude=sensor_longitude,
                epicentral_distance_km=epicentral_distance,
                hypocentral_distance_km=hypocentral_distance,
                p_arrival_seconds=p_arrival,
                detected_seconds=detected,
                processed_seconds=processed,
            )
        )

    alert_issuance = sorted(sensor.processed_seconds for sensor in sensors)[
        scenario.required_sensor_count - 1
    ]
    first_detection = min(sensor.detected_seconds for sensor in sensors)
    targets: list[TargetWarningResult] = []
    for target in scenario.targets:
        epicentral_distance = great_circle_distance_km(
            scenario.latitude,
            scenario.longitude,
            target.latitude,
            target.longitude,
        )
        hypocentral_distance = sqrt(epicentral_distance**2 + scenario.depth_km**2)
        p_arrival = hypocentral_distance / scenario.p_wave_velocity_km_s
        s_arrival = hypocentral_distance / scenario.s_wave_velocity_km_s
        lead = s_arrival - alert_issuance
        targets.append(
            TargetWarningResult(
                name=target.name,
                latitude=target.latitude,
                longitude=target.longitude,
                epicentral_distance_km=epicentral_distance,
                hypocentral_distance_km=hypocentral_distance,
                p_arrival_seconds=p_arrival,
                s_arrival_seconds=s_arrival,
                first_detection_seconds=first_detection,
                alert_issuance_seconds=alert_issuance,
                warning_lead_seconds=lead,
                status=warning_status(lead),
            )
        )

    return EarlyWarningSimulationResult(
        scenario=scenario,
        model=SimulationModelMetadata(
            name="Spherical surface distance with local depth correction",
            earth_radius_km=EARTH_RADIUS_KM,
            p_wave_velocity_km_s=scenario.p_wave_velocity_km_s,
            s_wave_velocity_km_s=scenario.s_wave_velocity_km_s,
            detection_delay_seconds=scenario.detection_delay_seconds,
            processing_delay_seconds=scenario.processing_delay_seconds,
            required_sensor_count=scenario.required_sensor_count,
            travel_time_formula=(
                "t = sqrt(d_surface^2 + depth^2) / velocity; "
                "d_surface uses the haversine great-circle distance."
            ),
            sensor_distribution=(
                "Synthetic locations use a deterministic golden-angle spiral within "
                "the configured radius; this is not a real station inventory."
            ),
            alert_rule=(
                "Alert issuance is the processed P-wave time of the configured Nth sensor; "
                "each sensor adds detection delay and then processing delay."
            ),
            limitations=[
                "Uniform wave velocities ignore heterogeneous geological structures.",
                "Depth correction uses a local right triangle, not a geocentric chord or ray "
                "tracing.",
                "Magnitude is recorded but does not affect modeled wave travel or timing.",
                "The network, detections, processing, and alert are synthetic model outputs.",
                "No operational EEW algorithm, communications latency, or ground motion is "
                "modeled.",
                "Positive lead time is not a delivery guarantee; negative lead means shaking "
                "is modeled first.",
            ],
        ),
        first_detection_seconds=first_detection,
        alert_issuance_seconds=alert_issuance,
        sensors=sensors,
        targets=targets,
    )