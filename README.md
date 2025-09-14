# Network Telemetry Aggregation System

## Overview
This project implements a network telemetry aggregation system inspired by NVIDIA’s UFM.  
It consists of two components:

1. **Telemetry Generator (`telemetry_generator.py`)**  
   - Simulates telemetry metrics (`bandwidth`, `latency`, `errors`) for multiple switches.  
   - Updates values every second.  
   - Serves a **CSV feed** at:  
     ```
     http://127.0.0.1:9001/counters
     ```
     Format:  
     ```
     switch_id,bandwidth,latency,errors,timestamp
     switch1,55.6,0.32,1,2025-09-14T12:30:05.123456+00:00
     ```

2. **Metrics Server (`metrics_server.py`)**  
   - Periodically fetches telemetry from the generator.  
   - Stores data in memory per switch and metric.  
   - Provides REST APIs for querying, aggregating, and observing telemetry.  
   - Tracks:
      - API requests & errors  
      - Latency per API  
      - Uptime since server start  
      - Enforces **freshness validation**: only accepts telemetry data ≤ 3 seconds old 

---

## Features
- **Real-time telemetry** updates every 1 second.  
- **Freshness checks**: stale data returns `503 Service Unavailable`.  
- **Historical values** stored per metric and switch.  
- **Aggregations**: 
   - Max latency  
   - Min bandwidth  
   - Total errors  
- **Observability**: request count, error count, avg/min/max API latency, uptime.   

---

## REST API Endpoints

### 1. Get a specific metric
```
GET /telemetry/get?switch_id=<id>&metric=<metric>
```
Example:
```bash
curl "http://127.0.0.1:8080/telemetry/get?switch_id=switch1&metric=bandwidth"
```
Response:
```json
{
  "switch_id": "switch1",
  "metric": "bandwidth",
  "value": 72.34,
  "timestamp": "2025-09-14T12:30:05.123456+00:00"
}
```

### 2. List a metric across all switches
```
GET /telemetry/list?metric=<metric>
```
Example:
```bash
curl "http://127.0.0.1:8080/telemetry/list?metric=latency"
```
Response:
```json
{
  "switch1": {"value": 0.45, "timestamp": "2025-09-14T12:30:05.123456+00:00"},
  "switch2": {"value": 0.67, "timestamp": "2025-09-14T12:30:05.123456+00:00"}
}
```

### 3. Aggregated metrics
```
GET /telemetry/aggregate
```
Returns **max latency, min bandwidth, and total errors** per switch:
```json
{
  "switch1": {"max_latency": 0.95, "min_bandwidth": 11.2, "total_errors": 12},
  "switch2": {"max_latency": 0.87, "min_bandwidth": 15.4, "total_errors": 9}
}
```

### 4. Stats & observability
```
GET /telemetry/stats
```
Example response:
```json
{
  "requests": 42,
  "errors": 3,
  "latency": {
    "get_metric": {"avg_latency": 0.0012, "min_latency": 0.0009, "max_latency": 0.0023},
    "list_metrics": {"avg_latency": 0.0015, "min_latency": 0.0011, "max_latency": 0.0028},
    "aggregate_metrics": {"avg_latency": 0.0013, "min_latency": 0.0010, "max_latency": 0.0021},
    "stats": {"avg_latency": 0.0009, "min_latency": 0.0008, "max_latency": 0.0011},
    "uptime_seconds": 123.45
  }
}
```

---

## Setup & Running

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate    # Windows

pip install aiohttp
```

### 2. Run telemetry generator
```bash
python telemetry_generator.py
```
Runs on `http://127.0.0.1:9001/counters`

### 3. Run metrics server
```bash
python metrics_server.py
```
Runs on `http://127.0.0.1:8080`

---

## Limitations
- Data is stored **in-memory only** (lost on restart).  
- Scalability limited to one machine and one thread.  
- No authentication/rate limiting.  

---

## Future Improvements
- Use **Redis / PostgreSQL** for persistent + scalable storage.  
- Support **streaming updates** (WebSockets, Kafka, gRPC) instead of polling.  
- Add **structured logging** & monitoring integration (Prometheus, Grafana).  
- Implement **authentication & rate limiting**.  
- Containerize with **Docker/Kubernetes** for deployment.  

