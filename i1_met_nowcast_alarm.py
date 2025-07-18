"""
Rain Warning AppDaemon App
Monitors MET.NO nowcast for rain and door sensors, sending notifications when both conditions are met.

Copyright (c) 2025 the_louie
"""

import appdaemon.plugins.hass.hassapi as hass
import json
from datetime import datetime, timedelta, timezone


class RainWarning(hass.Hass):
    """AppDaemon app for rain warning notifications when doors are open."""

    def initialize(self):
        """Initialize the rain warning app."""
        # Configuration
        self.nowcast_sensor = self.args.get("nowcast_sensor")
        self.door_sensors = self.args.get("door_window_sensors", [])
        self.persons = self.args.get("persons", [])

        # Validation
        if not all([self.nowcast_sensor, self.door_sensors, self.persons]):
            self.log("Error: Missing required configuration (nowcast_sensor, door_window_sensors, or persons)", level="ERROR")
            return

        # State tracking
        self.last_notification_time = None
        self.notification_cooldown = 180  # 3 minutes cooldown

        # Listen for state changes on door sensors
        for sensor in self.door_sensors:
            self.listen_state(self.check_rain_forecast, sensor)

        # Start periodic rain check
        self.run_every(self.check_rain_forecast, "now", 5 * 60)  # Every 5 minutes

    def check_rain_forecast(self, entity=None, attribute=None, old=None, new=None, **kwargs):
        """Check if rain is expected within 15 minutes and doors are open."""
        try:
            # Skip if door closed (only check when door opens)
            if entity and new != "on":
                return

            # First check rain forecast - if no rain expected, no need to check doors
            nowcast_state = self.get_state(self.nowcast_sensor, attribute="forecast_json")
            if not nowcast_state:
                return

            forecast_data = json.loads(nowcast_state)
            now = datetime.now(timezone.utc)
            threshold_time = now + timedelta(minutes=30)

            # Check for rain within 30 minutes
            rain_found = False
            rain_minutes = 0
            for forecast in forecast_data:
                if not forecast.get("datetime"):
                    continue

                forecast_time = datetime.fromisoformat(forecast["datetime"].replace("Z", "+00:00"))
                if forecast_time > threshold_time:
                    break  # No need to check further

                if (forecast_time >= now and
                    forecast.get("precipitation", 0) > 0):
                    rain_found = True
                    rain_minutes = int((forecast_time - now).total_seconds() / 60)
                    break

            if not rain_found:
                return  # No rain expected

            # Rain expected, now check if any doors are open
            for sensor in self.door_sensors:
                if self.get_state(sensor) == "on":
                    break
            else:
                return  # No doors open

            # Both conditions met, check cooldown and send notification
            if (self.last_notification_time is None or
                (now - self.last_notification_time).total_seconds() >= self.notification_cooldown):

                message = f"⚠️ Rain Warning: Rain expected in {rain_minutes} minutes and doors are open!"
                for person in self.persons:
                    notify_service = person.get("notify")
                    if notify_service:
                        self.call_service(f"notify/{notify_service}", message=message)

                self.last_notification_time = now
                self.log("Rain warning notification sent", level="INFO")

        except Exception as e:
            self.log(f"Error in check_rain_forecast: {e}", level="ERROR")
