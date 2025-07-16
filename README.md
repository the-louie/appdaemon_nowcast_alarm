# Rain Warning AppDaemon App

Copyright (c) 2025 the_louie

An AppDaemon app for Home Assistant that monitors MET.NO nowcast reports and sends notifications when rain is expected within 15 minutes and any door sensors indicate open doors.

## Features

- Monitors MET.NO nowcast weather data for precipitation forecasts
- Checks door/window sensor states
- Sends notifications when both conditions are met (rain expected + doors open)
- Includes notification cooldown to prevent spam
- Comprehensive error handling

## Configuration

Add the following to your `config.yaml`:

```yaml
rain_warning:
  module: i1_met_nowcast_alarm
  class: RainWarning

  nowcast_sensor: weather.met_no_nowcast_met_nowcast
  door_window_sensors:
    - binary_sensor.sovrum_balkong_door_sensor
    - binary_sensor.entredorr_door_sensor
    - binary_sensor.maggans_dorr_door_sensor
    - binary_sensor.vr_door_door_sensor
    - binary_sensor.kallardorren_door_sensor

  persons:
    - name: "anders"
      notify: "mobile_app_pixel_9_pro"
```

### Configuration Options

- `nowcast_sensor`: Entity ID of the MET.NO nowcast sensor
- `door_window_sensors`: List of door/window sensor entity IDs to monitor
- `persons`: List of persons to notify, each with a name and notification service

## How It Works

1. The app checks for rain every 5 minutes by parsing the `forecast_json` attribute from the MET.NO sensor
2. It monitors all configured door sensors for state changes
3. When a door opens, it immediately checks the rain forecast
4. If rain is expected within 15 minutes and any door is open, it sends notifications
5. A 5-minute cooldown prevents notification spam

## Requirements

- AppDaemon 4.x
- Home Assistant with MET.NO integration
- Door/window sensors configured in Home Assistant
- Notification services configured for the specified persons

## License

This project is licensed under the BSD 2-Clause License - see the [LICENSE](LICENSE) file for details.