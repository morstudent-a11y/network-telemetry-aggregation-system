import asyncio
import aiohttp
from aiohttp import web
import csv
import io
import time
import datetime
import pprint

TELEMETRY_URL = 'http://127.0.0.1:9001/counters'
telemetry_data = {}
api_stats = {'requests': 0, 'errors': 0}
# Latency stats per API
api_latency = {}
system_start_time = time.time()  # Record the start time

FRESHNESS_THRESHOLD_SECONDS = 3  # Accept data up to 3 seconds old

def record_latency(api_name, duration):
    stats = api_latency.setdefault(api_name, {'count': 0, 'total': 0.0, 'min': None, 'max': None})
    stats['count'] += 1
    stats['total'] += duration
    if stats['min'] is None or duration < stats['min']:
        stats['min'] = duration
    if stats['max'] is None or duration > stats['max']:
        stats['max'] = duration

def with_latency(api_name):
    def decorator(handler):
        async def wrapper(request):
            start = time.perf_counter()
            try:
                response = await handler(request)
                return response
            finally:
                duration = time.perf_counter() - start
                record_latency(api_name, duration)
        return wrapper
    return decorator

async def fetch_telemetry():
    global telemetry_data
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(TELEMETRY_URL) as resp:
                    text = await resp.text()
                    reader = csv.DictReader(io.StringIO(text))
                    for row in reader:
                        switch_id = row['switch_id']
                        if switch_id not in telemetry_data:
                            telemetry_data[switch_id] = {}
                        timestamp = row.get('timestamp')
                        for metric, value in row.items():
                            if metric == 'switch_id' or metric == 'timestamp':
                                continue
                            if metric not in telemetry_data[switch_id]:
                                telemetry_data[switch_id][metric] = []
                            # Store (timestamp, value) tuple
                            telemetry_data[switch_id][metric].append((timestamp, float(value)))
            except Exception as e:
                print('Error fetching telemetry:', e)
            await asyncio.sleep(1)

def is_fresh(timestamp_str):
    try:
        ts = datetime.datetime.fromisoformat(timestamp_str)
        now = datetime.datetime.now(datetime.UTC)
        age = (now - ts).total_seconds()
        return age <= FRESHNESS_THRESHOLD_SECONDS
    except Exception:
        return False

@with_latency('get_metric')
async def get_metric(request):
    api_stats['requests'] += 1
    switch_id = request.query.get('switch_id')
    metric = request.query.get('metric')
    try:
        # Get the latest (timestamp, value) tuple for the requested metric
        latest_timestamp, value = telemetry_data[switch_id][metric][-1]
        if not latest_timestamp or not is_fresh(latest_timestamp):
            api_stats['errors'] += 1
            return web.json_response({'error': 'Telemetry data is stale or missing'}, status=503)
        return web.json_response({'switch_id': switch_id, 'metric': metric, 'value': value, 'timestamp': latest_timestamp})
    except Exception:
        api_stats['errors'] += 1
        return web.json_response({'error': 'Metric not found'}, status=404)

@with_latency('list_metrics')
async def list_metrics(request):
    api_stats['requests'] += 1
    metric = request.query.get('metric')
    result = {}
    try:
        for switch_id, metrics in telemetry_data.items():
            if metric in metrics and metrics[metric]:
                latest_timestamp, value = metrics[metric][-1]
                if latest_timestamp and is_fresh(latest_timestamp):
                    result[switch_id] = {
                        'value': value,
                        'timestamp': latest_timestamp
                    }
        if not result:
            api_stats['errors'] += 1
            return web.json_response({'error': 'No fresh telemetry data found'}, status=503)
        return web.json_response(result)
    except Exception:
        api_stats['errors'] += 1
        return web.json_response({'error': 'Metric not found'}, status=404)

@with_latency('stats')
async def stats(request):
    uptime = time.time() - system_start_time  # Calculate uptime
    latency_stats = {}
    for api, stats_dict in api_latency.items():
        latency_stats[api] = {
            'avg_latency': stats_dict['total'] / stats_dict['count'] if stats_dict['count'] else 0,
            'min_latency': stats_dict['min'] if stats_dict['min'] is not None else 0,
            'max_latency': stats_dict['max'] if stats_dict['max'] is not None else 0,
        }
    latency_stats['uptime_seconds'] = uptime

    # Return all telemetry data in the response, pretty-printed
    return web.json_response(
        {**api_stats, 'latency': latency_stats}
    )

@with_latency('aggregate_metrics')
async def aggregate_metrics(request):
    result = {}
    for switch_id, metrics in telemetry_data.items():
        # Extract only the values for each metric (ignore timestamps)
        latencies = [v for (_, v) in metrics.get('latency', [])]
        bandwidths = [v for (_, v) in metrics.get('bandwidth', [])]
        errors = [v for (_, v) in metrics.get('errors', [])]
        result[switch_id] = {
            'max_latency': max(latencies) if latencies else 0,
            'min_bandwidth': min(bandwidths) if bandwidths else 0,
            'total_errors': sum(errors) if errors else 0
        }
    return web.json_response(result)

async def start_background_tasks(app):
    app['telemetry_fetcher'] = asyncio.create_task(fetch_telemetry())

async def cleanup_background_tasks(app):
    app['telemetry_fetcher'].cancel()
    await app['telemetry_fetcher']

app = web.Application()
app.router.add_get('/telemetry/get', get_metric)
app.router.add_get('/telemetry/list', list_metrics)
app.router.add_get('/telemetry/stats', stats)
app.router.add_get('/telemetry/aggregate', aggregate_metrics)

app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
