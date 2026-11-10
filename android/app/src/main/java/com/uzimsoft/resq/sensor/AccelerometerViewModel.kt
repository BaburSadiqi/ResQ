package com.uzimsoft.resq.sensor

import android.app.Application
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.SystemClock
import androidx.lifecycle.AndroidViewModel
import com.uzimsoft.resq.data.network.AggregatedSensorReport
import com.uzimsoft.resq.data.network.MobileNetworkReporter
import com.uzimsoft.resq.data.network.NetworkStatus
import com.uzimsoft.resq.data.network.BackendConnectionResult
import com.uzimsoft.resq.data.network.BackendDiscovery
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlin.math.sqrt
import com.uzimsoft.resq.data.network.ResearchAlert

enum class VibrationState {
    NORMAL,
    MOVEMENT_DETECTED,
    STRONG_VIBRATION,
}

data class SensorInfo(
    val name: String,
    val vendor: String,
    val type: String,
    val maximumRange: Float,
    val resolution: Float,
    val powerMilliAmp: Float,
)

data class MotionSample(
    val timestampNanos: Long,
    val x: Float,
    val y: Float,
    val z: Float,
    val magnitude: Float,
)

data class AccelerometerUiState(
    val isMonitoring: Boolean = false,
    val sensorAvailable: Boolean = false,
    val registrationError: String? = null,
    val usesLinearAcceleration: Boolean = false,
    val sensorInfo: SensorInfo? = null,
    val sensorAccuracy: String = "Awaiting readings",
    val samplingPeriodUs: Int = REQUESTED_INTERVAL_US,
    val latest: MotionSample? = null,
    val observedIntervalMs: Float? = null,
    val samples: List<MotionSample> = emptyList(),
    val vibrationState: VibrationState = VibrationState.NORMAL,
    val sessionDurationMs: Long = 0L,
    val peakMotionMagnitude: Float = 0f,
    val rmsMotionMagnitude: Float = 0f,
    val strongVibrationCrossings: Int = 0,
    val processedSamples: Long = 0L,
    val isLikelyEmulator: Boolean = false,
    val networkStatus: NetworkStatus = NetworkStatus.LOCAL_SENSOR_MODE,
    val backendUrl: String = "",
    val serverSettingsMessage: String? = null,
    val isTestingServer: Boolean = false,
    val discoveryStatus: String = "Searching...",
    val researchAlert: ResearchAlert? = null,
) {
    val observedRateHz: Float?
        get() = observedIntervalMs?.takeIf { it > 0f }?.let { 1_000f / it }

    companion object {
        const val REQUESTED_INTERVAL_US = 20_000
    }
}

class AccelerometerViewModel(application: Application) : AndroidViewModel(application), SensorEventListener {
    private val sensorManager = application.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val linearAcceleration = sensorManager.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION)
    private val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private val selectedSensor = linearAcceleration ?: accelerometer

    private val _uiState = MutableStateFlow(
        AccelerometerUiState(
            sensorAvailable = selectedSensor != null,
            usesLinearAcceleration = linearAcceleration != null,
            sensorInfo = selectedSensor?.toSensorInfo(),
            isLikelyEmulator = isLikelyEmulator(),
        ),
    )
    val uiState: StateFlow<AccelerometerUiState> = _uiState.asStateFlow()

    private var shouldMonitor = false
    private var hostStarted = false
    private var listenerRegistered = false
    private var lastTimestampNanos: Long? = null
    private var lastUiEmitNanos = 0L
    private var sessionSegmentStartedAtMs: Long? = null
    private var accumulatedDurationMs = 0L
    private var sumOfSquares = 0.0
    private var processedSamples = 0L
    private var peakMagnitude = 0f
    private var strongCrossings = 0
    private var previousState = VibrationState.NORMAL
    private var gravityX = 0f
    private var gravityY = 0f
    private var gravityZ = 0f
    private val graphSamples = ArrayDeque<MotionSample>(MAX_GRAPH_SAMPLES)
    private val networkReporter = MobileNetworkReporter(application) { status -> publish { it.copy(networkStatus = status) } }
    private var reportStartedAtMs = 0L
    private var reportSamples = 0
    private var reportSquares = 0.0
    private var reportPeak = 0f
    private lateinit var backendDiscovery: BackendDiscovery

    init {
        publish { it.copy(backendUrl = networkReporter.currentBackendUrl()) }
        networkReporter.onAlert = { alert -> publish { state -> state.copy(researchAlert = alert) } }
        backendDiscovery = networkReporter.discoverBackend(
            onState = { state -> publish { it.copy(discoveryStatus = state) } },
            onFound = { url -> publish { it.copy(backendUrl = url) } },
        )
    }

    fun scanForBackend() { backendDiscovery.scan() }
    fun dismissResearchAlert() { publish { it.copy(researchAlert = null) } }

    fun testBackendUrl(url: String) {
        publish { it.copy(isTestingServer = true, serverSettingsMessage = "Testing...") }
        networkReporter.testConnection(url) { result ->
            val message = when (result) {
                BackendConnectionResult.Connected -> "Connected to ResQ Backend"
                BackendConnectionResult.Failed -> "Connection failed"
                BackendConnectionResult.InvalidBackend -> "Invalid ResQ backend"
                is BackendConnectionResult.InvalidUrl -> result.message
            }
            publish { it.copy(isTestingServer = false, serverSettingsMessage = message) }
        }
    }

    fun saveBackendUrl(url: String) {
        try {
            networkReporter.changeBackendUrl(url)
            publish { it.copy(backendUrl = networkReporter.currentBackendUrl(), serverSettingsMessage = "Server URL saved.") }
        } catch (error: IllegalArgumentException) {
            publish { it.copy(serverSettingsMessage = error.message ?: "Invalid URL.") }
        }
    }

    fun startMonitoring() {
        if (selectedSensor == null) {
            _uiState.value = _uiState.value.copy(registrationError = "No motion sensor is available on this device.")
            return
        }
        shouldMonitor = true
        registerIfReady()
    }

    fun stopMonitoring() {
        shouldMonitor = false
        unregister()
        publish { it.copy(isMonitoring = false, sessionDurationMs = currentSessionDurationMs()) }
    }

    fun resetSession() {
        graphSamples.clear()
        accumulatedDurationMs = 0L
        sessionSegmentStartedAtMs = if (listenerRegistered) SystemClock.elapsedRealtime() else null
        sumOfSquares = 0.0
        processedSamples = 0L
        peakMagnitude = 0f
        strongCrossings = 0
        previousState = VibrationState.NORMAL
        lastTimestampNanos = null
        publish {
            it.copy(
                latest = null,
                observedIntervalMs = null,
                samples = emptyList(),
                vibrationState = VibrationState.NORMAL,
                sessionDurationMs = 0L,
                peakMotionMagnitude = 0f,
                rmsMotionMagnitude = 0f,
                strongVibrationCrossings = 0,
                processedSamples = 0L,
            )
        }
    }

    fun onHostStarted() {
        hostStarted = true
        registerIfReady()
    }

    fun onHostStopped() {
        hostStarted = false
        unregister()
        publish { it.copy(isMonitoring = false, sessionDurationMs = currentSessionDurationMs()) }
    }

    private fun registerIfReady() {
        val sensor = selectedSensor ?: return
        if (!hostStarted || !shouldMonitor || listenerRegistered) return

        lastTimestampNanos = null
        gravityX = 0f
        gravityY = 0f
        gravityZ = 0f
        val registered = sensorManager.registerListener(this, sensor, AccelerometerUiState.REQUESTED_INTERVAL_US)
        listenerRegistered = registered
        if (registered) {
            sessionSegmentStartedAtMs = SystemClock.elapsedRealtime()
            resetReportWindow()
            networkReporter.start(sensor, selectedSensor.toSensorInfo())
            publish { it.copy(isMonitoring = true, registrationError = null) }
        } else {
            publish {
                it.copy(
                    isMonitoring = false,
                    registrationError = "Android could not register the selected motion sensor.",
                )
            }
        }
    }

    private fun unregister() {
        if (!listenerRegistered) return
        val startedAt = sessionSegmentStartedAtMs
        if (startedAt != null) {
            accumulatedDurationMs += SystemClock.elapsedRealtime() - startedAt
        }
        sessionSegmentStartedAtMs = null
        sensorManager.unregisterListener(this)
        listenerRegistered = false
        lastTimestampNanos = null
        networkReporter.stop()
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor != selectedSensor) return
        val sample = motionSample(event)
        val intervalMs = lastTimestampNanos?.let { (event.timestamp - it) / 1_000_000f }
        lastTimestampNanos = event.timestamp

        processedSamples += 1
        sumOfSquares += sample.magnitude.toDouble() * sample.magnitude
        peakMagnitude = maxOf(peakMagnitude, sample.magnitude)
        val vibrationState = vibrationStateFor(sample.magnitude)
        if (vibrationState == VibrationState.STRONG_VIBRATION && previousState != VibrationState.STRONG_VIBRATION) {
            strongCrossings += 1
        }
        previousState = vibrationState
        accumulateReport(sample, vibrationState)

        if (event.timestamp - lastUiEmitNanos < UI_EMIT_INTERVAL_NANOS) return
        lastUiEmitNanos = event.timestamp
        graphSamples.addLast(sample)
        if (graphSamples.size > MAX_GRAPH_SAMPLES) graphSamples.removeFirst()

        val rms = sqrt((sumOfSquares / processedSamples).toFloat())
        publish {
            it.copy(
                latest = sample,
                observedIntervalMs = intervalMs,
                samples = graphSamples.toList(),
                vibrationState = vibrationState,
                sessionDurationMs = currentSessionDurationMs(),
                peakMotionMagnitude = peakMagnitude,
                rmsMotionMagnitude = rms,
                strongVibrationCrossings = strongCrossings,
                processedSamples = processedSamples,
            )
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        if (sensor != selectedSensor) return
        publish { it.copy(sensorAccuracy = accuracyLabel(accuracy)) }
    }

    private fun motionSample(event: SensorEvent): MotionSample {
        val rawX = event.values[0]
        val rawY = event.values[1]
        val rawZ = event.values[2]
        val x: Float
        val y: Float
        val z: Float
        if (selectedSensor?.type == Sensor.TYPE_LINEAR_ACCELERATION) {
            x = rawX
            y = rawY
            z = rawZ
        } else if (lastTimestampNanos == null) {
            // Seed the gravity estimate to prevent a stationary first reading being classified as motion.
            gravityX = rawX
            gravityY = rawY
            gravityZ = rawZ
            x = 0f
            y = 0f
            z = 0f
        } else {
            gravityX = HIGH_PASS_ALPHA * gravityX + (1f - HIGH_PASS_ALPHA) * rawX
            gravityY = HIGH_PASS_ALPHA * gravityY + (1f - HIGH_PASS_ALPHA) * rawY
            gravityZ = HIGH_PASS_ALPHA * gravityZ + (1f - HIGH_PASS_ALPHA) * rawZ
            x = rawX - gravityX
            y = rawY - gravityY
            z = rawZ - gravityZ
        }
        return MotionSample(event.timestamp, x, y, z, sqrt(x * x + y * y + z * z))
    }

    private fun vibrationStateFor(magnitude: Float): VibrationState = when {
        magnitude >= STRONG_VIBRATION_THRESHOLD -> VibrationState.STRONG_VIBRATION
        magnitude >= MOVEMENT_THRESHOLD -> VibrationState.MOVEMENT_DETECTED
        else -> VibrationState.NORMAL
    }

    private fun currentSessionDurationMs(): Long {
        val segment = sessionSegmentStartedAtMs?.let { SystemClock.elapsedRealtime() - it } ?: 0L
        return accumulatedDurationMs + segment
    }

    private fun resetReportWindow() {
        reportStartedAtMs = SystemClock.elapsedRealtime(); reportSamples = 0; reportSquares = 0.0; reportPeak = 0f
    }

    private fun accumulateReport(sample: MotionSample, state: VibrationState) {
        if (reportStartedAtMs == 0L) resetReportWindow()
        reportSamples += 1; reportSquares += sample.magnitude.toDouble() * sample.magnitude; reportPeak = maxOf(reportPeak, sample.magnitude)
        val duration = SystemClock.elapsedRealtime() - reportStartedAtMs
        if (duration < REPORT_INTERVAL_MS || reportSamples == 0) return
        networkReporter.report(AggregatedSensorReport(duration, reportSamples, reportSamples * 1_000f / duration, state, reportPeak, sqrt((reportSquares / reportSamples).toFloat()), selectedSensor?.stringType ?: "UNKNOWN"))
        resetReportWindow()
    }

    private inline fun publish(transform: (AccelerometerUiState) -> AccelerometerUiState) {
        _uiState.value = transform(_uiState.value)
    }

    override fun onCleared() {
        backendDiscovery.stop()
        networkReporter.stopAlertPolling()
        unregister()
        super.onCleared()
    }

    private companion object {
        const val MAX_GRAPH_SAMPLES = 150
        const val UI_EMIT_INTERVAL_NANOS = 100_000_000L
        const val HIGH_PASS_ALPHA = 0.8f
        const val MOVEMENT_THRESHOLD = 1.5f
        const val STRONG_VIBRATION_THRESHOLD = 4.0f
        const val REPORT_INTERVAL_MS = 1_000L

        fun accuracyLabel(accuracy: Int): String = when (accuracy) {
            SensorManager.SENSOR_STATUS_ACCURACY_HIGH -> "High"
            SensorManager.SENSOR_STATUS_ACCURACY_MEDIUM -> "Medium"
            SensorManager.SENSOR_STATUS_ACCURACY_LOW -> "Low"
            SensorManager.SENSOR_STATUS_UNRELIABLE -> "Unreliable"
            else -> "Unknown"
        }

        fun Sensor.toSensorInfo() = SensorInfo(
            name = name,
            vendor = vendor,
            type = stringType,
            maximumRange = maximumRange,
            resolution = resolution,
            powerMilliAmp = power,
        )

        fun isLikelyEmulator(): Boolean =
            Build.FINGERPRINT.startsWith("generic") ||
                Build.MODEL.contains("Emulator", ignoreCase = true) ||
                Build.MODEL.contains("Android SDK built for", ignoreCase = true)
    }
}
