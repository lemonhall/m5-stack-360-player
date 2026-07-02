# M5StickC Plus2 官方示例来源记录

日期：2026-07-02

## 已检查的官方来源

- M5StickCPlus2 官方 IMU 示例：
  `https://github.com/m5stack/M5StickCPlus2/blob/master/examples/Basic/imu/imu.ino`
- M5StickCPlus2 库元数据：
  `https://github.com/m5stack/M5StickCPlus2/blob/master/library.properties`
- M5Unified IMU 示例：
  `https://github.com/m5stack/M5Unified/blob/master/examples/Basic/Imu/Imu.ino`

## 结论

- M5StickCPlus2 官方示例使用 `#include "M5StickCPlus2.h"`。
- 初始化流程为 `auto cfg = M5.config();` 和 `StickCP2.begin(cfg);`。
- IMU 数据通过 `StickCP2.Imu.update()` 和 `StickCP2.Imu.getImuData()` 读取。
- Plus2 官方示例直接暴露加速度计和陀螺仪字段。
- v1 获取到的 Plus2 示例没有直接暴露立方体渲染或融合后的 yaw/pitch/roll。
- M5Unified IMU 示例有更丰富的屏幕可视化和校准流程，但不是 Plus2 专用立方体渲染示例。

## v1 决策

v1 以官方 M5StickCPlus2 IMU API 作为硬件基线，并保留设备屏幕上的实时 IMU/姿态数值可视化。由于 v1 获取到的 Plus2 官方示例没有直接提供融合后的 yaw/pitch/roll 或立方体输出，v1 固件新增了轻量的陀螺仪积分姿态估计用于遥测，同时每个遥测包仍保留原始加速度计和陀螺仪数据。

如果后续找到官方 Plus2 立方体专用示例，可以通过 ECN 替换显示部分，而不改变 PC 端遥测协议。
