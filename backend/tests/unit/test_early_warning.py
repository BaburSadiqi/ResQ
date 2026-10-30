from math import asin, degrees, sin

from app.main import app
from app.schemas.early_warning import (
    EarlyWarningSimulationRequest,
    TargetLocation,
)
from app.services.early_warning import (
    great_circle_distance_km,
    simulate_early_warning,
    warning_status,
)
from fastapi.testclient import TestClient


def scenario(**overrides) -> EarlyWarningSimulationRequest:
    values = {
        "latitude": 34.5,
        "longitude": 67.1,
        "magnitude": 5.8,
        "depth_km": 10,
        "sensor_count": 4,
        "required_sensor_count": 2,
        "sensor_radius_km": 100,
        "targets": [TargetLocation(name="Example", latitude=35, longitude=68)],
    }
    return EarlyWarningSimulationRequest(**(values | overrides))


def test_hypocentral_travel_times_and_quorum_alert() -> None:
    result = simulate_early_warning(
        scenario(
            latitude=0,
            longitude=0,
            depth_km=0,
            sensor_count=2,
            required_sensor_count=2,
            detection_delay_seconds=1,
            processing_delay_seconds=2,
            targets=[TargetLocation(name="Epicenter", latitude=0, longitude=0)],
        )
    )
    assert result.targets[0].epicentral_distance_km == 0
    assert result.targets[0].p_arrival_seconds == 0
    assert result.targets[0].s_arrival_seconds == 0
    processed_times = sorted(sensor.processed_seconds for sensor in result.sensors)
    assert result.alert_issuance_seconds == processed_times[1]
    assert all(
        sensor.processed_seconds == sensor.p_arrival_seconds + 3 for sensor in result.sensors
    )

    depth_result = simulate_early_warning(
        scenario(
            latitude=0,
            longitude=0,
            depth_km=10,
            sensor_count=1,
            required_sensor_count=1,
            targets=[TargetLocation(name="Epicenter", latitude=0, longitude=0)],
        )
    )
    assert depth_result.targets[0].p_arrival_seconds == 10 / 6
    assert depth_result.targets[0].s_arrival_seconds == 10 / 3.5


def test_surface_distance_uses_haversine() -> None:
    assert abs(great_circle_distance_km(0, 0, 0, 1) - 111.195) < 0.01
    assert abs(great_circle_distance_km(0, 179, 0, -179) - 222.39) < 0.02


def test_maximum_depth_and_identical_inputs_are_deterministic() -> None:
    inputs = scenario(
        latitude=89.9,
        longitude=179.9,
        depth_km=700,
        sensor_count=3,
        required_sensor_count=2,
        targets=[TargetLocation(name="Epicenter", latitude=89.9, longitude=179.9)],
    )
    first = simulate_early_warning(inputs)
    second = simulate_early_warning(inputs)

    assert first.model_dump() == second.model_dump()
    target = first.targets[0]
    assert target.epicentral_distance_km == 0
    assert target.hypocentral_distance_km == 700
    assert target.p_arrival_seconds == 700 / inputs.p_wave_velocity_km_s
    assert target.s_arrival_seconds == 700 / inputs.s_wave_velocity_km_s
    assert all(sensor.detected_seconds >= sensor.p_arrival_seconds for sensor in first.sensors)
    assert all(sensor.processed_seconds >= sensor.detected_seconds for sensor in first.sensors)


def test_warning_lead_statuses_include_positive_zero_and_negative() -> None:
    base = {
        "latitude": 0,
        "longitude": 0,
        "depth_km": 0,
        "sensor_count": 1,
        "required_sensor_count": 1,
        "sensor_radius_km": 10,
        "detection_delay_seconds": 0,
        "processing_delay_seconds": 0,
    }
    positive = simulate_early_warning(
        scenario(**base, targets=[TargetLocation(name="Far", latitude=0, longitude=1)])
    )
    negative = simulate_early_warning(
        scenario(**base, targets=[TargetLocation(name="Near", latitude=0, longitude=0)])
    )
    alert_time = positive.alert_issuance_seconds
    zero_distance = alert_time * 3.5
    zero_longitude = degrees(2 * asin(sin(zero_distance / (2 * 6371))))
    zero = simulate_early_warning(
        scenario(
            **base,
            targets=[TargetLocation(name="Boundary", latitude=0, longitude=zero_longitude)],
        )
    )

    assert positive.targets[0].warning_lead_seconds > 0
    assert positive.targets[0].status == "potential_lead_time"
    assert abs(zero.targets[0].warning_lead_seconds) <= 1e-9
    assert zero.targets[0].status == "no_useful_lead_time"
    assert negative.targets[0].warning_lead_seconds < 0
    assert negative.targets[0].status == "shaking_before_alert"
    assert warning_status(0) == "no_useful_lead_time"


def test_simulation_api_returns_model_and_timeline() -> None:
    response = TestClient(app).post(
        "/api/v1/scenarios/early-warning", json=scenario().model_dump()
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"]["earth_radius_km"] == 6371
    assert len(payload["sensors"]) == 4
    assert payload["first_detection_seconds"] == min(
        sensor["detected_seconds"] for sensor in payload["sensors"]
    )
    assert payload["targets"][0]["first_detection_seconds"] == payload[
        "first_detection_seconds"
    ]
    assert payload["targets"][0]["alert_issuance_seconds"] == payload["alert_issuance_seconds"]


def test_simulation_api_rejects_invalid_coordinates_and_wave_speeds() -> None:
    client = TestClient(app)
    invalid_coordinate = scenario().model_dump()
    invalid_coordinate["latitude"] = 91
    assert (
        client.post("/api/v1/scenarios/early-warning", json=invalid_coordinate).status_code
        == 422
    )

    invalid_speeds = scenario().model_dump()
    invalid_speeds["p_wave_velocity_km_s"] = 3
    invalid_speeds["s_wave_velocity_km_s"] = 4
    assert client.post("/api/v1/scenarios/early-warning", json=invalid_speeds).status_code == 422

    invalid_depth = scenario().model_dump()
    invalid_depth["depth_km"] = 701
    assert client.post("/api/v1/scenarios/early-warning", json=invalid_depth).status_code == 422

    invalid_target = scenario().model_dump()
    invalid_target["targets"][0]["longitude"] = 181
    assert client.post("/api/v1/scenarios/early-warning", json=invalid_target).status_code == 422

    invalid_delay = scenario().model_dump()
    invalid_delay["detection_delay_seconds"] = -0.1
    assert client.post("/api/v1/scenarios/early-warning", json=invalid_delay).status_code == 422


def test_request_rejects_quorum_above_sensor_count() -> None:
    try:
        scenario(sensor_count=2, required_sensor_count=3)
    except ValueError as error:
        assert "cannot exceed" in str(error)
    else:
        raise AssertionError("Expected invalid sensor quorum to be rejected")