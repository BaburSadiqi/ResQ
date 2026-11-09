package com.uzimsoft.resq

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import com.uzimsoft.resq.ui.ResQDashboard
import com.uzimsoft.resq.ui.theme.ResQTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ResQTheme {
                Surface(color = MaterialTheme.colorScheme.background) {
                    ResQDashboard()
                }
            }
        }
    }
}
