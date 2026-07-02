# 塔山循环日志

| 日期 | 版本 | 里程碑 | 成本档位 | 评审上下文 | 发现阻塞数 | 逃逸缺陷数 | 固化检查数 | 耗时分钟 | 备注 |
|---|---|---|---|---|---:|---:|---:|---:|---|
| 2026-07-02 | v1 | docs | light | same-model | 0 | 0 | 0 | 10 | 初始文档写作；仓库初始为空且未初始化 git |
| 2026-07-02 | v1 | implementation | standard | same-model | 1 | 0 | 1 | 120 | 固件构建/上传/串口 JSON 验证通过；BLE live 因 bleak 安装超时阻塞；M5.update 崩溃已固化静态回归测试 |
| 2026-07-02 | v2 | VLC player | standard | same-model | 0 | 0 | 3 | 90 | GUI-first VLC 360 player；固化 config ignore、viewpoint mapper/controller tests、forbidden-control scan |
