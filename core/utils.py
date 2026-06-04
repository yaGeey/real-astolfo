import requests
from datetime import datetime

def get_dusk_time():
    try:
        res = requests.get('https://api.sunrisesunset.io/json?lat=50.4501&lng=30.5234', timeout=5)
        dusk_str = res.json()['results']['dusk']
        dusk_time = datetime.strptime(dusk_str, '%I:%M:%S %p')
        dawn_str = res.json()['results']['dawn']
        dawn_time = datetime.strptime(dawn_str, '%I:%M:%S %p')
        return [dusk_time.time(), dawn_time.time()]
    except:
        return [datetime.strptime('20:00', '%H:%M').time(), datetime.strptime('06:00', '%H:%M').time()]