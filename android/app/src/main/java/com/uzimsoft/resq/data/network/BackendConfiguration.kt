package com.uzimsoft.resq.data.network

import android.content.Context
import com.uzimsoft.resq.BuildConfig
import java.net.URI

/** Persistent, validated backend location. The build configuration remains the fallback. */
class BackendConfiguration(context: Context) {
    private val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    fun currentUrl(): String = preferences.getString(DISCOVERED_URL_KEY, null)
        ?: preferences.getString(BACKEND_URL_KEY, null) ?: defaultUrl

    fun manualUrl(): String = preferences.getString(BACKEND_URL_KEY, null) ?: defaultUrl

    fun save(url: String) {
        preferences.edit().putString(BACKEND_URL_KEY, validateAndNormalize(url)).apply()
    }

    fun saveDiscovered(url: String) {
        preferences.edit().putString(DISCOVERED_URL_KEY, validateAndNormalize(url)).apply()
    }

    fun clearDiscovered() { preferences.edit().remove(DISCOVERED_URL_KEY).apply() }

    fun validateAndNormalize(value: String): String {
        val candidate = value.trim()
        if (candidate.isEmpty()) throw IllegalArgumentException("Enter a backend URL.")
        val uri = try { URI(candidate) } catch (_: Exception) {
            throw IllegalArgumentException("Enter a valid http:// or https:// URL.")
        }
        if (uri.scheme?.lowercase() !in setOf("http", "https") || uri.host.isNullOrBlank()) {
            throw IllegalArgumentException("URL must include http:// or https:// and a valid host.")
        }
        if (uri.userInfo != null || uri.query != null || uri.fragment != null ||
            (uri.path != null && uri.path.isNotEmpty() && uri.path != "/") || uri.port !in -1..65535) {
            throw IllegalArgumentException("Enter only the backend server address, optionally with a port.")
        }
        return "${uri.scheme.lowercase()}://${uri.host}${if (uri.port == -1) "" else ":${uri.port}"}/"
    }

    private val defaultUrl: String
        get() = BuildConfig.RESQ_BACKEND_URL.trimEnd('/') + "/"

    private companion object {
        const val PREFERENCES_NAME = "resq_mobile"
        const val BACKEND_URL_KEY = "backend_url"
        const val DISCOVERED_URL_KEY = "discovered_backend_url"
    }
}
