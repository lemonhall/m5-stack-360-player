# M5StickC Plus2 Official Example Source

Date: 2026-07-02

## Official Sources Checked

- M5StickCPlus2 official IMU example:
  `https://github.com/m5stack/M5StickCPlus2/blob/master/examples/Basic/imu/imu.ino`
- M5StickCPlus2 library metadata:
  `https://github.com/m5stack/M5StickCPlus2/blob/master/library.properties`
- M5Unified IMU example:
  `https://github.com/m5stack/M5Unified/blob/master/examples/Basic/Imu/Imu.ino`

## Findings

- The M5StickCPlus2 official example uses `#include "M5StickCPlus2.h"`.
- Setup calls `auto cfg = M5.config();` and `StickCP2.begin(cfg);`.
- IMU data is read with `StickCP2.Imu.update()` and `StickCP2.Imu.getImuData()`.
- Official Plus2 example exposes accelerometer and gyroscope fields directly.
- The fetched Plus2 example does not expose a cube renderer or fused yaw/pitch/roll directly.
- The M5Unified IMU example has a richer on-screen visualization and calibration flow, but it is not Plus2-specific cube rendering.

## v1 Decision

v1 uses the official M5StickCPlus2 IMU API as the hardware baseline and keeps an on-device screen visualization of live IMU/pose values. Because the official Plus2 example fetched for v1 does not directly provide fused yaw/pitch/roll or cube output, v1 firmware adds a lightweight gyro-integrated orientation estimate for telemetry, while keeping raw accelerometer and gyroscope data in every packet.

If a later official cube-specific Plus2 example is found, it can replace the display section via ECN without changing the PC telemetry protocol.
