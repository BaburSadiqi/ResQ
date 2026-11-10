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
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit
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
    private val backendConfiguration = BackendConfiguration(context)
    private val alertExecutor = Executors.newSingleThreadScheduledExecutor()
    private var alertPolling: ScheduledFuture<*>? = null
    private val alertPreferences = context.getSharedPreferences("resq_mobile", Context.MODE_PRIVATE)
    private val deviceId = context.getSharedPreferences("resq_mobile", Context.MODE_PRIVATE)
        .getString("device_id", null) ?: UUID.randomUUID().toString().also {
            context.getSharedPreferences("resq_mobile", Context.MODE_PRIVATE).edit().putString("device_id", it).apply()
        }
    private var registered = false
    private var lastHeartbeatMs = 0L

    fun currentBackendUrl(): String = backendConfiguration.currentUrl()

    fun changeBackendUrl(url: String) {
        backendConfiguration.save(url)
        backendConfiguration.clearDiscovered()
        registered = false
        lastHeartbeatMs = 0L
        onStatus(NetworkStatus.CONNECTING)
    }

    fun testConnection(url: String, callback: (BackendConnectionResult) -> Unit) {
        val normalized = try { backendConfiguration.validateAndNormalize(url) } catch (error: IllegalArgumentException) {
            callback(BackendConnectionResult.InvalidUrl(error.message ?: "Invalid URL."))
            return
        }
        executor.execute { callback(checkHealth(normalized)) }
    }

    fun discoverBackend(onState: (String) -> Unit, onFound: (String) -> Unit): BackendDiscovery {
        backendConfiguration.clearDiscovered()
        return BackendDiscovery(context, ::testConnection, { url -> backendConfiguration.saveDiscovered(url); onFound(url) }, onState).also { it.scan() }
    }

    fun pollAlerts(callback: (ResearchAlert) -> Unit) {
        if (alertPolling != null) return
        alertPolling = alertExecutor.scheduleAtFixedRate({
            try {
                val response = get("api/v1/mobile/devices/$deviceId/alerts/latest") ?: return@scheduleAtFixedRate
                val id = response.optString("event_id")
                if (id.isBlank() || id == alertPreferences.getString("last_alert_id", null)) return@scheduleAtFixedRate
                alertPreferences.edit().putString("last_alert_id", id).apply()
                callback(ResearchAlert(id, response.optString("created_at"), response.optInt("device_count", 2), response.optDouble("maximum_peak", 0.0)))
            } catch (_: Exception) { }
        }, 0, 1, TimeUnit.SECONDS)
    }

    fun stopAlertPolling() { alertPolling?.cancel(false); alertPolling = null }

    fun start(sensor: Sensor?, sensorInfo: SensorInfo?) {
        if (sensor == null) return
        onStatus(NetworkStatus.CONNECTING)
        executor.execute {
            registered = register(sensorInfo)
            onStatus(if (registered) NetworkStatus.CONNECTED else NetworkStatus.BACKEND_UNAVAILABLE)
            if (registered) pollAlerts { onAlert?.invoke(it) }
        }
    }

    fun report(report: AggregatedSensorReport) {
        executor.execute {
            if (!registered) {
                registered = register(null)
                if (registered) pollAlerts { onAlert?.invoke(it) }
            }
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

    fun stop() { stopAlertPolling(); onStatus(NetworkStatus.LOCAL_SENSOR_MODE) }

    var onAlert: ((ResearchAlert) -> Unit)? = null

    private fun register(sensorInfo: SensorInfo?): Boolean = post("api/v1/mobile/devices/register", JSONObject().apply {
        put("device_id", deviceId); put("manufacturer", Build.MANUFACTURER); put("model", Build.MODEL)
        put("android_version", Build.VERSION.RELEASE); put("app_version", BuildConfig.VERSION_NAME)
        sensorInfo?.let { put("sensor_name", it.name); put("sensor_vendor", it.vendor); put("sensor_resolution", it.resolution); put("sensor_maximum_range", it.maximumRange) }
    })

    private fun checkHealth(baseUrl: String): BackendConnectionResult = try {
        (URL(baseUrl + "api/v1/mobile/health").openConnection() as HttpURLConnection).run {
            requestMethod = "GET"; connectTimeout = 4_000; readTimeout = 4_000
            setRequestProperty("Accept", "application/json")
            val body = if (responseCode in 200..299) inputStream.bufferedReader().use { it.readText() } else ""
            val isResq = try {
                val json = JSONObject(body)
                json.optString("status") == "ok" && json.optString("service") == "resq-mobile-network"
            } catch (_: Exception) { false }
            disconnect()
            if (isResq) BackendConnectionResult.Connected else BackendConnectionResult.InvalidBackend
        }
    } catch (_: Exception) { BackendConnectionResult.Failed }

    private fun post(path: String, body: JSONObject?): Boolean = try {
        (URL(backendConfiguration.currentUrl() + path).openConnection() as HttpURLConnection).run {
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

    private fun get(path: String): JSONObject? = try {
        (URL(backendConfiguration.currentUrl() + path).openConnection() as HttpURLConnection).run {
            requestMethod = "GET"; connectTimeout = 2_000; readTimeout = 2_000
            val response = if (responseCode in 200..299) inputStream.bufferedReader().use { JSONObject(it.readText()) } else null
            disconnect(); response
        }
    } catch (_: Exception) { null }

    private companion object { const val HEARTBEAT_INTERVAL_MS = 12_000L }
}

data class ResearchAlert(val eventId: String, val createdAt: String, val deviceCount: Int, val maximumPeak: Double)

sealed interface BackendConnectionResult {
    data object Connected : BackendConnectionResult
    data object Failed : BackendConnectionResult
    data object InvalidBackend : BackendConnectionResult
    data class InvalidUrl(val message: String) : BackendConnectionResult
}
