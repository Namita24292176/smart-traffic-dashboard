import random
import uuid
from datetime import datetime, timezone


class BaseSensor:
    def __init__(self, sensor_id, location, rate_seconds=2.0):
        self.sensor_id = sensor_id
        self.sensor_type = self.__class__.__name__
        self.location = location
        self.rate = rate_seconds

    def read(self):
        raise NotImplementedError

    def payload(self):
        return {
            "id": str(uuid.uuid4()),
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type,
            "location": self.location,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": self.read()
        }


class VehicleCounterSensor(BaseSensor):
    def read(self):
        hour = datetime.now().hour
        peak = 7 <= hour <= 9 or 16 <= hour <= 18
        base = 35 if peak else 10

        return {
            "vehicle_count": random.randint(max(0, base - 8), base + 15),
            "heavy_vehicles": random.randint(0, 4),
            "interval_secs": self.rate
        }


class SpeedRadarSensor(BaseSensor):
    def read(self):
        avg = round(random.gauss(52, 11), 1)
        mx = round(avg + random.uniform(5, 28), 1)

        return {
            "avg_speed_kmh": max(0.0, avg),
            "max_speed_kmh": max(0.0, mx),
            "speeding_flag": mx > 80,
            "sample_size": random.randint(5, 40)
        }


class TrafficLightSensor(BaseSensor):
    PHASES = ["GREEN", "YELLOW", "RED", "RED_PED"]
    DURATIONS = {
        "GREEN": 30,
        "YELLOW": 5,
        "RED": 35,
        "RED_PED": 10
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._idx = 0
        self._elapsed = 0.0

    def read(self):
        phase = self.PHASES[self._idx % len(self.PHASES)]

        self._elapsed += self.rate

        if self._elapsed >= self.DURATIONS[phase]:
            self._idx += 1
            self._elapsed = 0.0

        return {
            "phase": phase,
            "queue_length": random.randint(0, 25) if phase.startswith("RED") else random.randint(0, 4),
            "phase_elapsed_s": round(self._elapsed, 1)
        }


class AirQualitySensor(BaseSensor):
    def read(self):
        pm25 = max(0.0, round(random.gauss(18, 7), 2))
        co2 = max(350, round(random.gauss(420, 38), 1))

        if pm25 < 12:
            category = "Good"
        elif pm25 < 35:
            category = "Moderate"
        elif pm25 < 55:
            category = "Unhealthy for sensitive groups"
        else:
            category = "Unhealthy"

        return {
            "pm25_ugm3": pm25,
            "co2_ppm": co2,
            "aqi_category": category,
            "temperature_c": round(random.gauss(14, 5), 1)
        }


class PedestrianSensor(BaseSensor):
    def read(self):
        hour = datetime.now().hour
        base = 5 if 8 <= hour <= 18 else 1

        count = max(0, int(random.gauss(base, 2)))

        return {
            "pedestrian_count": count,
            "crossing_requested": count > 0 and random.random() > 0.55,
            "wait_time_s": random.randint(0, 60) if count > 0 else 0
        }