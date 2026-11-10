package com.uzimsoft.resq.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.AlertDialog
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.platform.LocalContext
import android.content.Context
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.uzimsoft.resq.sensor.AccelerometerUiState
import com.uzimsoft.resq.sensor.AccelerometerViewModel
import com.uzimsoft.resq.sensor.MotionSample
import com.uzimsoft.resq.sensor.VibrationState
import com.uzimsoft.resq.data.network.NetworkStatus
import java.util.Locale
import kotlin.math.max

@Composable
fun ResQDashboard(viewModel: AccelerometerViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(lifecycleOwner, viewModel) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> viewModel.onHostStarted()
                Lifecycle.Event.ON_STOP -> viewModel.onHostStopped()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        if (lifecycleOwner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) {
            viewModel.onHostStarted()
        }
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            viewModel.onHostStopped()
        }
    }

    DashboardContent(
        state = uiState,
        onStart = viewModel::startMonitoring,
        onStop = viewModel::stopMonitoring,
        onReset = viewModel::resetSession,
        onTestServer = viewModel::testBackendUrl,
        onSaveServer = viewModel::saveBackendUrl,
        onScanBackend = viewModel::scanForBackend,
        onDismissAlert = viewModel::dismissResearchAlert,
    )
}

@Composable
private fun DashboardContent(
    state: AccelerometerUiState,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onReset: () -> Unit,
    onTestServer: (String) -> Unit,
    onSaveServer: (String) -> Unit,
    onScanBackend: () -> Unit,
    onDismissAlert: () -> Unit,
) {
    state.researchAlert?.let { alert -> ResearchAlertDialog(alert, onDismissAlert) }
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item(key = "header", contentType = "header") {
            Header(state)
        }
        item(key = "mode", contentType = "status") {
            ModeBanner(state)
        }
        item(key = "monitor", contentType = "card") {
            MonitoringCard(state)
        }
        item(key = "graph", contentType = "card") {
            MotionGraph(state)
        }
        item(key = "controls", contentType = "controls") {
            MonitoringControls(state, onStart, onStop, onReset)
        }
        item(key = "server-settings", contentType = "settings") {
            ServerSettings(state, onTestServer, onSaveServer, onScanBackend)
        }
        item(key = "statistics", contentType = "card") {
            SessionStatistics(state)
        }
        item(key = "sensor-info", contentType = "card") {
            SensorInformation(state)
        }
        item(key = "research", contentType = "info") {
            ResearchInformation()
        }
    }
}

@Composable
private fun Header(state: AccelerometerUiState) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "ResQ",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = "Earthquake Research & Sensor Network",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        StatusPill(
            label = if (state.isMonitoring) "Sensor Active" else "Sensor Stopped",
            color = if (state.isMonitoring) SuccessGreen else MaterialTheme.colorScheme.outline,
        )
    }
}

@Composable
private fun ModeBanner(state: AccelerometerUiState) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
            Text(
                text = state.networkStatus.name.replace('_', ' '),
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = if (state.isLikelyEmulator) {
                    "Emulator environment detected. Use a physical phone for genuine hardware readings."
                } else {
                    when (state.networkStatus) {
                        NetworkStatus.CONNECTED -> "Sensor summaries are reaching the ResQ backend."
                        NetworkStatus.CONNECTING -> "Connecting while local sensor monitoring continues."
                        NetworkStatus.BACKEND_UNAVAILABLE -> "Backend unavailable; local sensor monitoring continues."
                        NetworkStatus.LOCAL_SENSOR_MODE -> "This session uses on-device motion sensors only."
                    } + " Backend: " + state.backendUrl
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ServerSettings(
    state: AccelerometerUiState,
    onTestServer: (String) -> Unit,
    onSaveServer: (String) -> Unit,
    onScanBackend: () -> Unit,
) {
    var backendUrl by rememberSaveable(state.backendUrl) { mutableStateOf(state.backendUrl) }
    Card(shape = RoundedCornerShape(24.dp)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Server Settings", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("Backend Server", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
            Text("Backend Discovery", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
            Text(state.discoveryStatus, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedButton(onClick = onScanBackend, modifier = Modifier.fillMaxWidth()) { Text("SCAN AGAIN") }
            DetailRow("Current server", state.backendUrl)
            OutlinedTextField(
                value = backendUrl,
                onValueChange = { backendUrl = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Backend URL") },
                placeholder = { Text("http://192.168.1.10:8000/") },
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(
                    onClick = { onTestServer(backendUrl) },
                    enabled = !state.isTestingServer,
                    modifier = Modifier.weight(1f),
                ) { Text(if (state.isTestingServer) "TESTING..." else "TEST CONNECTION") }
                Button(onClick = { onSaveServer(backendUrl) }, modifier = Modifier.weight(1f)) { Text("SAVE") }
            }
            state.serverSettingsMessage?.let { message ->
                val color = when (message) {
                    "Connected to ResQ Backend", "Server URL saved." -> SuccessGreen
                    else -> MaterialTheme.colorScheme.error
                }
                Text(message, color = color, style = MaterialTheme.typography.bodySmall)
            }
            Text(
                "Phone and backend computer must be reachable on the same local network for LAN demo mode.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ResearchAlertDialog(alert: com.uzimsoft.resq.data.network.ResearchAlert, onDismiss: () -> Unit) {
    val context = LocalContext.current
    LaunchedEffect(alert.eventId) {
        val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) vibrator?.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 250, 150, 250), -1))
        else @Suppress("DEPRECATION") vibrator?.vibrate(longArrayOf(0, 250, 150, 250), -1)
        ToneGenerator(AudioManager.STREAM_NOTIFICATION, 90).startTone(ToneGenerator.TONE_PROP_BEEP, 500)
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("SUSPECTED SEISMIC EVENT", color = WarningRed, fontWeight = FontWeight.ExtraBold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Correlated vibration detected by ${alert.deviceCount} devices.", fontWeight = FontWeight.Bold)
                Text("Event time: ${alert.createdAt}")
                Text("Maximum peak: %.2f m/s²".format(Locale.US, alert.maximumPeak))
                Text("Research prototype — not a confirmed earthquake.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        },
        confirmButton = { Button(onClick = onDismiss) { Text("DISMISS") } },
    )
}

@Composable
private fun MonitoringCard(state: AccelerometerUiState) {
    val stateColor = vibrationColor(state.vibrationState)
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(24.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("LIVE MOTION", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                    Text(
                        text = state.vibrationState.label(),
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = stateColor,
                    )
                }
                StatusPill(state.sensorAccuracy, stateColor)
            }

            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    text = state.latest?.magnitude?.let(::number) ?: "—",
                    style = MaterialTheme.typography.displayMedium,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = "m/s²",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 10.dp),
                )
            }
            Text(
                text = if (state.usesLinearAcceleration) {
                    "Linear acceleration sensor: gravity excluded by hardware."
                } else {
                    "Accelerometer with high-pass gravity removal (approximation)."
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            HorizontalDivider()
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AxisMetric("X", state.latest?.x, BlueAccent, Modifier.weight(1f))
                AxisMetric("Y", state.latest?.y, PurpleAccent, Modifier.weight(1f))
                AxisMetric("Z", state.latest?.z, SuccessGreen, Modifier.weight(1f))
            }
            DetailRow("Sampling rate", state.observedRateHz?.let { number(it) + " Hz" } ?: "Awaiting samples")
        }
    }
}

@Composable
private fun AxisMetric(label: String, value: Float?, color: Color, modifier: Modifier) {
    Surface(
        modifier = modifier,
        color = color.copy(alpha = 0.10f),
        shape = RoundedCornerShape(14.dp),
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(label, color = color, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
            Text(value?.let(::number) ?: "—", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text("m/s²", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun MotionGraph(state: AccelerometerUiState) {
    Card(shape = RoundedCornerShape(24.dp)) {
        Column(Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Real-time motion history", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(
                        text = if (state.samples.isEmpty()) "Awaiting real sensor readings" else "Last " + state.samples.size + " display samples",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("Peak", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(number(state.peakMotionMagnitude) + " m/s²", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(Modifier.height(14.dp))
            MotionChart(samples = state.samples)
            Text(
                text = "Scale adapts to the real session peak. Values represent local motion acceleration.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

@Composable
private fun MotionChart(samples: List<MotionSample>) {
    Canvas(Modifier.fillMaxWidth().height(190.dp)) {
        val gridColor = Color.White.copy(alpha = 0.10f)
        val topValue = max(samples.maxOfOrNull { it.magnitude } ?: 0f, 1f)
        repeat(5) { index ->
            val y = size.height * index / 4f
            drawLine(gridColor, Offset(0f, y), Offset(size.width, y), strokeWidth = 1f)
        }
        if (samples.size > 1) {
            val path = Path()
            for (index in samples.indices) {
                val x = index * size.width / (samples.size - 1)
                val y = size.height - (samples[index].magnitude / topValue * size.height)
                if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            drawPath(path, BlueAccent, style = Stroke(width = 4f))
            val last = samples.last().magnitude
            val y = size.height - (last / topValue * size.height)
            drawCircle(color = PurpleAccent, radius = 7f, center = Offset(size.width, y))
        }
    }
}

@Composable
private fun MonitoringControls(
    state: AccelerometerUiState,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onReset: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        if (state.isMonitoring) {
            OutlinedButton(onClick = onStop, modifier = Modifier.fillMaxWidth()) {
                Text("STOP MONITORING")
            }
        } else {
            Button(onClick = onStart, enabled = state.sensorAvailable, modifier = Modifier.fillMaxWidth()) {
                Text("START MONITORING")
            }
        }
        OutlinedButton(onClick = onReset, modifier = Modifier.fillMaxWidth()) {
            Text("RESET SESSION")
        }
        state.registrationError?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun SessionStatistics(state: AccelerometerUiState) {
    Card(shape = RoundedCornerShape(24.dp)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Session statistics", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            StatisticRow("Monitoring duration", formatDuration(state.sessionDurationMs), "Peak motion", number(state.peakMotionMagnitude) + " m/s²")
            StatisticRow("RMS motion", number(state.rmsMotionMagnitude) + " m/s²", "Strong crossings", state.strongVibrationCrossings.toString())
            StatisticRow("Approx. sample rate", state.observedRateHz?.let { number(it) + " Hz" } ?: "—", "Processed samples", state.processedSamples.toString())
            Text(
                text = "Thresholds are configurable demonstration values: movement ≥ 1.5 m/s²; strong vibration ≥ 4.0 m/s².",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun StatisticRow(leftLabel: String, leftValue: String, rightLabel: String, rightValue: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        StatisticCell(leftLabel, leftValue, Modifier.weight(1f))
        StatisticCell(rightLabel, rightValue, Modifier.weight(1f))
    }
}

@Composable
private fun StatisticCell(label: String, value: String, modifier: Modifier) {
    Column(
        modifier = modifier
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(12.dp))
            .padding(12.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun SensorInformation(state: AccelerometerUiState) {
    Card(shape = RoundedCornerShape(24.dp)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Sensor information", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            state.sensorInfo?.let { info ->
                DetailRow("Name", info.name)
                DetailRow("Vendor", info.vendor)
                DetailRow("Type", info.type)
                DetailRow("Maximum range", number(info.maximumRange) + " m/s²")
                DetailRow("Resolution", number(info.resolution) + " m/s²")
                DetailRow("Power", number(info.powerMilliAmp) + " mA")
                DetailRow("Requested interval", (state.samplingPeriodUs / 1_000).toString() + " ms")
            } ?: Text("No compatible motion sensor was reported by Android.", color = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun DetailRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(0.42f))
        Text(value, fontWeight = FontWeight.Medium, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.End, modifier = Modifier.weight(0.58f))
    }
}

@Composable
private fun ResearchInformation() {
    Surface(
        color = PurpleAccent.copy(alpha = 0.10f),
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Research & safety", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = PurpleAccent)
            Text(
                "ResQ is a research prototype for studying smartphone-based vibration sensing and multi-device earthquake early-warning concepts.",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                "A single smartphone cannot confirm an earthquake. Sensor measurements and warning states in this application are experimental and are not a validated public earthquake warning service.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun StatusPill(label: String, color: Color) {
    Surface(color = color.copy(alpha = 0.14f), shape = RoundedCornerShape(100.dp)) {
        Row(Modifier.padding(horizontal = 10.dp, vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(color = color, shape = CircleShape, modifier = Modifier.size(8.dp)) {}
            Spacer(Modifier.width(6.dp))
            Text(label, color = color, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
        }
    }
}

private fun VibrationState.label(): String = when (this) {
    VibrationState.NORMAL -> "NORMAL"
    VibrationState.MOVEMENT_DETECTED -> "MOVEMENT DETECTED"
    VibrationState.STRONG_VIBRATION -> "STRONG VIBRATION"
}

private fun vibrationColor(state: VibrationState): Color = when (state) {
    VibrationState.NORMAL -> SuccessGreen
    VibrationState.MOVEMENT_DETECTED -> AmberAccent
    VibrationState.STRONG_VIBRATION -> WarningRed
}

private fun number(value: Float): String = String.format(Locale.US, "%.2f", value)

private fun formatDuration(milliseconds: Long): String {
    val seconds = milliseconds / 1_000
    val minutes = seconds / 60
    return if (minutes > 0) minutes.toString() + "m " + (seconds % 60).toString() + "s" else seconds.toString() + "s"
}

private val BlueAccent = Color(0xFF5CB8FF)
private val PurpleAccent = Color(0xFFB89CFF)
private val SuccessGreen = Color(0xFF62D59A)
private val AmberAccent = Color(0xFFFFC35A)
private val WarningRed = Color(0xFFFF776B)
