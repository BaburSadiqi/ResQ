# ResQ exhibition demo

This is a research prototype for multi-device correlated vibration detection. A correlated event is not a confirmed earthquake.

## Startup

1. Start PostgreSQL.
2. Apply migrations: `cd backend; alembic upgrade head`.
3. Start the API on all LAN interfaces: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. In another terminal, install dependencies and advertise the API: `python -m pip install -r requirements.txt; python advertise_resq.py`.
5. Start the frontend with `cd frontend; npm run dev -- --host 0.0.0.0`.
6. Connect the laptop and both phones to the same Wi-Fi.
7. Open ResQ on both phones. Server Settings should show `ResQ Backend Found` and `CONNECTED`.
8. Start monitoring on both phones and verify both are ONLINE in the dashboard.

## Demonstration

- Shake only one phone strongly: it should show STRONG VIBRATION, with no correlated alert.
- Shake both phones strongly within approximately 3 seconds: one correlated event is created and both participating phones show a SUSPECTED SEISMIC EVENT research alert.
- Confirm the latest correlated event in the dashboard.

The two phones registered to the same backend are treated as the same demonstration sensor network; GPS/geographic validation is intentionally not used.

## Emergency fallback

If automatic discovery is unavailable, enter the laptop's current IPv4 address (for example `http://192.168.1.10:8000/`) in Server Settings and save it.
