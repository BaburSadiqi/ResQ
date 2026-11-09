from math import asin, degrees, sin

from fastapi.testclient import TestClient

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


def test_frontend_default_alert_quorum_and_multiple_target_timings() -> None:
    result = simulate_early_warning(
        EarlyWarningSimulationRequest(
            latitude=34.5,
            longitude=67.1,
            magnitude=5.8,
            depth_km=15,
            detection_delay_seconds=0.8,
            processing_delay_seconds=0.5,
            sensor_count=8,
            required_sensor_count=2,
            sensor_radius_km=250,
            p_wave_velocity_km_s=6,
            s_wave_velocity_km_s=3.5,
            targets=[
                TargetLocation(name="Kabul (example)", latitude=34.5553, longitude=69.2075),
                TargetLocation(name="Kandahar (example)", latitude=31.6289, longitude=65.7372),
                TargetLocation(name="Herat (example)", latitude=34.3529, longitude=62.204),
            ],
        )
    )

    ordered_sensors = sorted(result.sensors, key=lambda sensor: sensor.processed_seconds)
    assert [sensor.id for sensor in ordered_sensors[:2]] == ["SYN-01", "SYN-02"]
    assert all(sensor.epicentral_distance_km <= 250 for sensor in result.sensors)
    assert abs(ordered_sensors[0].p_arrival_seconds - 89.65210538520623 / 6) < 1e-12
    assert abs(ordered_sensors[1].p_arrival_seconds - 125.89678312014428 / 6) < 1e-12
    assert ordered_sensors[0].detected_seconds == ordered_sensors[0].p_arrival_seconds + 0.8
    assert ordered_sensors[0].processed_seconds == ordered_sensors[0].detected_seconds + 0.5
    assert abs(result.alert_issuance_seconds - 22.282797186690715) < 1e-12
    assert result.alert_issuance_seconds == ordered_sensors[1].processed_seconds

    targets = {target.name: target for target in result.targets}
    expected = {
        "Kabul (example)": (193.15876535180692, 32.29005205951999, 55.35437495917712),
        "Kandahar (example)": (343.5721669351016, 57.31657552878315, 98.25698662077112),
        "Herat (example)": (449.3121408212482, 74.9270756375404, 128.44641537864067),
    }
    for name, (distance, p_arrival, s_arrival) in expected.items():
        target = targets[name]
        assert abs(target.epicentral_distance_km - distance) < 1e-9
        assert abs(target.p_arrival_seconds - p_arrival) < 1e-9
        assert abs(target.s_arrival_seconds - s_arrival) < 1e-9
        assert abs(target.warning_lead_seconds - (s_arrival - result.alert_issuance_seconds)) < 1e-9
        assert target.status == "potential_lead_time"


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
    alert_time = simulate_early_warning(
        scenario(**base, targets=[TargetLocation(name="Probe", latitude=0, longitude=0)])
    ).alert_issuance_seconds
    zero_distance = alert_time * 3.5
    zero_longitude = degrees(2 * asin(sin(zero_distance / (2 * 6371))))
    multiple = simulate_early_warning(
        scenario(
            **base,
            targets=[
                TargetLocation(name="Near", latitude=0, longitude=0),
                TargetLocation(name="Boundary", latitude=0, longitude=zero_longitude),
                TargetLocation(name="Far", latitude=0, longitude=1),
            ],
        )
    )

    by_name = {target.name: target for target in multiple.targets}
    assert by_name["Far"].warning_lead_seconds > 0
    assert by_name["Far"].status == "potential_lead_time"
    assert abs(by_name["Boundary"].warning_lead_seconds) <= 1e-9
    assert by_name["Boundary"].status == "no_useful_lead_time"
    assert by_name["Near"].warning_lead_seconds < 0
    assert by_name["Near"].status == "shaking_before_alert"
    assert by_name["Near"].s_arrival_seconds < multiple.alert_issuance_seconds
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


def test_frontend_early_warning_request_shape_and_network_radius() -> None:
    payload = {
        "latitude": 34.5,
        "longitude": 67.1,
        "magnitude": 5.8,
        "depth_km": 10,
        "detection_delay_seconds": 0.8,
        "processing_delay_seconds": 0.5,
        "sensor_count": 4,
        "required_sensor_count": 2,
        "sensor_radius_km": 35,
        "p_wave_velocity_km_s": 6,
        "s_wave_velocity_km_s": 3.5,
        "targets": [{"name": "Example", "latitude": 35, "longitude": 68}],
    }
    response = TestClient(app).post("/api/v1/scenarios/early-warning", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["scenario"] == payload
    assert all(
        sensor["epicentral_distance_km"] <= payload["sensor_radius_km"]
        for sensor in result["sensors"]
    )


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