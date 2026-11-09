package com.uzimsoft.resq.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val ResQDarkColors = darkColorScheme(
    primary = Color(0xFF5CB8FF),
    onPrimary = Color(0xFF001D32),
    secondary = Color(0xFFB89CFF),
    tertiary = Color(0xFF62D59A),
    background = Color(0xFF07111F),
    onBackground = Color(0xFFE7F1FF),
    surface = Color(0xFF0D1B2A),
    onSurface = Color(0xFFE7F1FF),
    surfaceVariant = Color(0xFF162B42),
    onSurfaceVariant = Color(0xFFBAC8D9),
    outline = Color(0xFF7C8C9F),
    outlineVariant = Color(0xFF33495F),
    error = Color(0xFFFF776B),
)

@Composable
fun ResQTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = ResQDarkColors,
        typography = androidx.compose.material3.Typography(),
        content = content,
    )
}
