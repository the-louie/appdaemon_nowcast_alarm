"""
Rain Warning AppDaemon App
Monitors MET.NO nowcast for rain and door sensors, sending notifications when both conditions are met.

Copyright (c) 2025 the_louie
"""

import appdaemon.plugins.hass.hassapi as hass
import json
import os
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

        # Logging setup
        self.log_dir = os.path.join(os.path.dirname(__file__), "logs")
        self.ensure_log_directory()

        # Listen for state changes on door sensors
        for sensor in self.door_sensors:
            self.listen_state(self.check_rain_forecast, sensor)

        # Start periodic rain check
        self.run_every(self.check_rain_forecast, "now", 5 * 60)  # Every 5 minutes

    def ensure_log_directory(self):
        """Ensure the log directory exists."""
        try:
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
        except Exception as e:
            self.log(f"Error creating log directory: {e}", level="ERROR")

    def log_notification_debug(self, forecast_data, rain_found, rain_minutes, door_states, trigger_entity=None, trigger_state=None):
        """Log debug information when a notification is sent."""
        try:
            now = datetime.now(timezone.utc)
            log_filename = f"rain_warning_debug_{now.strftime('%Y%m%d')}.log"
            log_path = os.path.join(self.log_dir, log_filename)

            debug_info = {
                "timestamp": now.isoformat(),
                "trigger": {
                    "entity": trigger_entity,
                    "old_state": None,
                    "new_state": trigger_state
                },
                "forecast_analysis": {
                    "total_forecasts": len(forecast_data),
                    "rain_found": rain_found,
                    "rain_minutes": rain_minutes,
                    "forecast_data": forecast_data
                },
                "door_states": door_states,
                "notification_cooldown": {
                    "last_notification": self.last_notification_time.isoformat() if self.last_notification_time else None,
                    "cooldown_remaining": max(0, self.notification_cooldown - (now - self.last_notification_time).total_seconds()) if self.last_notification_time else 0
                },
                "configuration": {
                    "nowcast_sensor": self.nowcast_sensor,
                    "door_sensors": self.door_sensors,
                    "persons": self.persons
                }
            }

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"RAIN WARNING NOTIFICATION DEBUG LOG\n")
                f.write(f"{'='*80}\n")
                f.write(f"Timestamp: {debug_info['timestamp']}\n")
                f.write(f"Trigger: {debug_info['trigger']}\n")
                f.write(f"Rain Found: {rain_found} (in {rain_minutes} minutes)\n")
                f.write(f"Door States: {door_states}\n")
                f.write(f"Cooldown: {debug_info['notification_cooldown']}\n")
                f.write(f"Configuration: {debug_info['configuration']}\n")
                f.write(f"Full Forecast Data: {json.dumps(forecast_data, indent=2)}\n")
                f.write(f"{'='*80}\n")

            self.log(f"Debug information logged to {log_path}", level="INFO")

        except Exception as e:
            self.log(f"Error logging debug information: {e}", level="ERROR")

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
            door_states = {}
            doors_open = False
            for sensor in self.door_sensors:
                state = self.get_state(sensor)
                door_states[sensor] = state
                if state == "on":
                    doors_open = True

            if not doors_open:
                return  # No doors open

            # Both conditions met, check cooldown and send notification
            if (self.last_notification_time is None or
                (now - self.last_notification_time).total_seconds() >= self.notification_cooldown):

                # Log debug information before sending notification
                self.log_notification_debug(
                    forecast_data=forecast_data,
                    rain_found=rain_found,
                    rain_minutes=rain_minutes,
                    door_states=door_states,
                    trigger_entity=entity,
                    trigger_state=new
                )

                message = f"⚠️ Rain Warning: Rain expected in {rain_minutes} minutes and doors are open!"
                for person in self.persons:
                    notify_service = person.get("notify")
                    if notify_service:
                        self.call_service(f"notify/{notify_service}", message=message)

                self.last_notification_time = now
                self.log("Rain warning notification sent", level="INFO")

        except Exception as e:
            self.log(f"Error in check_rain_forecast: {e}", level="ERROR")
