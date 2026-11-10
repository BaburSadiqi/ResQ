package com.uzimsoft.resq.data.network

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Handler
import android.os.Looper

/** Best-effort LAN DNS-SD discovery. Manual configuration remains the fallback. */
class BackendDiscovery(
    context: Context,
    private val verify: (String, (BackendConnectionResult) -> Unit) -> Unit,
    private val onFound: (String) -> Unit,
    private val onState: (String) -> Unit,
) {
    private val nsd = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private var listener: NsdManager.DiscoveryListener? = null
    private val timeoutHandler = Handler(Looper.getMainLooper())
    private val timeout = Runnable { if (listener != null) { onState("Automatic discovery unavailable\nUsing manual server"); stop() } }

    fun scan() {
        stop()
        onState("Searching...")
        val discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(regType: String) = Unit
            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                if (!serviceInfo.serviceType.contains("_resq._tcp")) return
                nsd.resolveService(serviceInfo, object : NsdManager.ResolveListener {
                    override fun onResolveFailed(info: NsdServiceInfo, errorCode: Int) = Unit
                    override fun onServiceResolved(info: NsdServiceInfo) {
                        val host = info.host?.hostAddress ?: return
                        val candidate = "http://$host:${info.port}/"
                        verify(candidate) { result ->
                            if (result == BackendConnectionResult.Connected) {
                                onFound(candidate)
                                onState("ResQ Backend Found\n$host:${info.port}\nCONNECTED")
                                stop()
                            }
                        }
                    }
                })
            }
            override fun onServiceLost(serviceInfo: NsdServiceInfo) = Unit
            override fun onDiscoveryStopped(serviceType: String) = Unit
            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) { onState("Automatic discovery unavailable") ; stop() }
            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) { listener = null }
        }
        listener = discoveryListener
        nsd.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener)
        timeoutHandler.postDelayed(timeout, 5_000)
    }

    fun stop() {
        timeoutHandler.removeCallbacks(timeout)
        listener?.let { runCatching { nsd.stopServiceDiscovery(it) } }
        listener = null
    }

    private companion object { const val SERVICE_TYPE = "_resq._tcp." }
}
