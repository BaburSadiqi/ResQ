# ResQ mobile sensor network demo

The Android application keeps raw accelerometer samples on the phone. While monitoring, it sends one measured, compact aggregation per approximately one second to the FastAPI backend. Registration uses a random UUID saved in Android SharedPreferences; it is not a hardware identifier. Heartbeats run no more often than every 12 seconds.

## Configure a physical phone

Find the laptop LAN IPv4 address in PowerShell:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*'} | Format-Table IPAddress,InterfaceAlias
```

Build with that address (replace the example address), from `android/`:

```powershell
.\gradlew.bat assembleDebug -PRESQ_BACKEND_URL=http://192.168.1.50:8000/
```

The single Android base-URL configuration is `RESQ_BACKEND_URL` in `android/app/build.gradle.kts`. Its default (`http://10.0.2.2:8000/`) is for an Android emulator only. Debug builds intentionally permit cleartext HTTP for a same-Wi-Fi LAN demonstration; release builds do not add that exception.

Ensure the phone and laptop are on the same Wi-Fi and permit private-network inbound TCP port 8000 if Windows Firewall asks. `localhost` on the phone is the phone, not the laptop.

## Start the demo

```powershell
cd backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In a separate terminal:

```powershell
cd frontend
npm.cmd run dev -- --host 0.0.0.0
```

Set `RESQ_CORS_ORIGINS` to a comma-separated list of browser origins when the frontend is not using the default Vite local origins. Then install the debug APK, open it, and select **START MONITORING**. The dashboard polls the mobile endpoints every two seconds.

The network indicator can show **BACKEND UNAVAILABLE** without affecting local sensor monitoring. The dashboard labels readings as experimental sensor motion; it does not infer or confirm earthquakes.
