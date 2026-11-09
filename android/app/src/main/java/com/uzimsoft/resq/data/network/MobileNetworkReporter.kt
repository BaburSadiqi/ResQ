package com.uzimsoft.resq.data.network

import android.content.Context
import android.hardware.Sensor
import android.os.Build
import com.uzimsoft.resq.BuildConfig
import com.uzimsoft.resq.sensor.SensorInfo
import com.uzimsoft.resq.sensor.VibrationState
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.util.UUID
import java.util.concurrent.Executors
import org.json.JSONObject

enum class NetworkStatus { LOCAL_SENSOR_MODE, CONNECTING, CONNECTED, BACKEND_UNAVAILABLE }

data class AggregatedSensorReport(
    val durationMs: Long,
    val sampleCount: Int,
    val samplingRateHz: Float,
    val motionState: VibrationState,
    val peakAcceleration: Float,
    val rmsAcceleration: Float,
    val sensorType: String,
)

/** Sends bounded, one-second sensor summaries; raw sensor events never leave the phone. */
class MobileNetworkReporter(
    private val context: Context,
    private val onStatus: (NetworkStatus) -> Unit,
) {
    private val executor = Executors.newSingleThreadExecutor()
    private val deviceId = context.getSharedPreferences("resq_mobile", Context.MODE_PRIVATE)
        .getString("device_id", null) ?: UUID.randomUUID().toString().also {
            context.getSharedPreferences("resq_mobile", Context.MODE_PRIVATE).edit().putString("device_id", it).apply()
        }
    private var registered = false
    private var lastHeartbeatMs = 0L

    fun start(sensor: Sensor?, sensorInfo: SensorInfo?) {
        if (sensor == null) return
        onStatus(NetworkStatus.CONNECTING)
        executor.execute {
            registered = register(sensorInfo)
            onStatus(if (registered) NetworkStatus.CONNECTED else NetworkStatus.BACKEND_UNAVAILABLE)
        }
    }

    fun report(report: AggregatedSensorReport) {
        executor.execute {
            if (!registered) registered = register(null)
            if (!registered || !post("api/v1/mobile/sensor-reports", JSONObject().apply {
                    put("device_id", deviceId); put("recorded_at", Instant.now().toString())
                    put("duration_ms", report.durationMs); put("sample_count", report.sampleCount)
                    put("sampling_rate_hz", report.samplingRateHz); put("motion_state", report.motionState.apiName())
                    put("peak_acceleration", report.peakAcceleration); put("rms_acceleration", report.rmsAcceleration)
                    put("sensor_type", report.sensorType)
                })) { onStatus(NetworkStatus.BACKEND_UNAVAILABLE); return@execute }
            val now = System.currentTimeMillis()
            if (now - lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS) {
                if (!post("api/v1/mobile/devices/$deviceId/heartbeat", null)) { onStatus(NetworkStatus.BACKEND_UNAVAILABLE); return@execute }
                lastHeartbeatMs = now
            }
            onStatus(NetworkStatus.CONNECTED)
        }
    }

    fun stop() { onStatus(NetworkStatus.LOCAL_SENSOR_MODE) }

    private fun register(sensorInfo: SensorInfo?): Boolean = post("api/v1/mobile/devices/register", JSONObject().apply {
        put("device_id", deviceId); put("manufacturer", Build.MANUFACTURER); put("model", Build.MODEL)
        put("android_version", Build.VERSION.RELEASE); put("app_version", BuildConfig.VERSION_NAME)
        sensorInfo?.let { put("sensor_name", it.name); put("sensor_vendor", it.vendor); put("sensor_resolution", it.resolution); put("sensor_maximum_range", it.maximumRange) }
    })

    private fun post(path: String, body: JSONObject?): Boolean = try {
        (URL(BuildConfig.RESQ_BACKEND_URL + path).openConnection() as HttpURLConnection).run {
            requestMethod = "POST"; connectTimeout = 4_000; readTimeout = 4_000
            setRequestProperty("Accept", "application/json")
            if (body != null) { doOutput = true; setRequestProperty("Content-Type", "application/json"); outputStream.use { it.write(body.toString().toByteArray()) } }
            val ok = responseCode in 200..299
            disconnect(); ok
        }
    } catch (_: Exception) { false }

    private fun VibrationState.apiName() = when (this) {
        VibrationState.NORMAL -> "NORMAL"
        VibrationState.MOVEMENT_DETECTED -> "MOVEMENT"
        VibrationState.STRONG_VIBRATION -> "STRONG_VIBRATION"
    }

    private companion object { const val HEARTBEAT_INTERVAL_MS = 12_000L }
}
