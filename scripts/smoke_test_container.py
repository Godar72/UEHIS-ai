import os
import subprocess
import json
import hashlib

def run_container_test():
    py_code = """
import os, sys, json, urllib.request, urllib.error, hashlib

key = os.getenv('OPENWEATHER_API_KEY', '')
if not key or len(key) != 32:
    print(json.dumps({'target': 'container', 'status': 'CONFIG_ERROR', 'error': f'Key length {len(key)}'}))
    sys.exit(0)

key_hash = hashlib.sha256(key.encode()).hexdigest()[:8]
url = f'http://api.openweathermap.org/data/2.5/air_pollution?lat=18.5204&lon=73.8567&appid={key}'
req = urllib.request.Request(url, headers={'User-Agent': 'UEHIS-ContainerTest/1.0'})

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        pm2_5 = data.get('list', [{}])[0].get('components', {}).get('pm2_5')
        pm10 = data.get('list', [{}])[0].get('components', {}).get('pm10')
        aqi = data.get('list', [{}])[0].get('main', {}).get('aqi')
        is_valid = isinstance(pm2_5, (int, float)) and isinstance(pm10, (int, float))
        print(json.dumps({
            'target': 'container',
            'status': resp.status,
            'key_hash': key_hash,
            'valid_metrics': is_valid,
            'pm2_5': pm2_5,
            'pm10': pm10,
            'aqi': aqi
        }))
except urllib.error.HTTPError as e:
    print(json.dumps({
        'target': 'container',
        'status': e.code,
        'key_hash': key_hash,
        'error_message': e.reason
    }))
except Exception as exc:
    print(json.dumps({
        'target': 'container',
        'status': 'ERROR',
        'key_hash': key_hash,
        'error_message': str(exc)
    }))
"""
    cmd = ["docker", "exec", "uehis-api", "python", "-c", py_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout.strip())
        return data
    except Exception as e:
        return {'target': 'container', 'status': 'PARSE_ERROR', 'raw': res.stdout.strip(), 'stderr': res.stderr.strip()}

if __name__ == '__main__':
    result = run_container_test()
    print("CONTAINER TEST RESULT:")
    for k, v in result.items():
        print(f"  {k}: {v}")
