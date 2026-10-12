# Data sources and provenance

The initial source is the official [USGS FDSN Event Web Service](https://earthquake.usgs.gov/fdsnws/event/1/), requested in documented GeoJSON format. Each imported record keeps the USGS event identifier, source update time, source URL, and selected original properties.

USGS catalog records describe earthquakes that have been detected, located, and published. They are not a real-time sensor feed, an earthquake prediction mechanism, or a validated early-warning alert. Simulations and experimental assessments must remain separately labeled in later phases.
