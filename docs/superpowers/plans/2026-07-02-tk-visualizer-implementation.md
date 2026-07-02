# Tk 姿态可视化实现计划

> **给 agentic worker 的要求：**实现本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行。步骤使用 checkbox（`- [ ]`）语法追踪。

**目标：**构建一个 tkinter PC 可视化器，把实时 M5StickC Plus2 BLE 姿态渲染为橙黄色 3D 小棒。

**架构：**几何计算保持在 `pc_receiver.visualization` 中，纯函数且可测试；tkinter 和 BLE 线程编排放在 `pc_receiver.visualizer_app` 中。复用已有 parser、BLE transport、无 recorder 的 calibration state 和项目脚本入口。

**技术栈：**Python 3.13、tkinter、asyncio、`bleak` 可选依赖、pytest。

---

### 任务 1：纯 3D 几何

**文件：**
- 创建：`pc_receiver/visualization.py`
- 创建：`tests/test_visualization.py`

- [ ] **步骤 1：编写失败测试**

创建测试，断言中性姿态投影为水平小棒、yaw 改变端点位置、投影输出有限 2D 点。

- [ ] **步骤 2：运行测试**

运行：`python -m pytest tests\test_visualization.py`
预期：失败，因为 `pc_receiver.visualization` 尚不存在。

- [ ] **步骤 3：实现几何模块**

创建 `CuboidModel`、`rotation_matrix_from_ypr`、`transform_points` 和 `project_points`。

- [ ] **步骤 4：验证**

运行：`python -m pytest tests\test_visualization.py`
预期：通过。

### 任务 2：Tkinter 可视化应用

**文件：**
- 创建：`pc_receiver/visualizer_app.py`
- 修改：`pyproject.toml`
- 修改：`tests/test_python_runtime_policy.py`

- [ ] **步骤 1：编写失败的脚本元数据测试**

添加断言：`project.scripts["m5-visualizer"] == "pc_receiver.visualizer_app:main"`。

- [ ] **步骤 2：运行测试**

运行：`python -m pytest tests\test_python_runtime_policy.py`
预期：失败，因为脚本尚未声明。

- [ ] **步骤 3：实现应用和脚本入口**

添加 tkinter 应用，启动 BLE worker 线程，通过 `queue.Queue` 接收快照并在 canvas 上重绘长方体。在 `pyproject.toml` 中添加 `m5-visualizer` 脚本。

- [ ] **步骤 4：验证元数据和导入**

运行：`python -m pytest tests\test_python_runtime_policy.py`
运行：`uv run --extra ble python -c "from pc_receiver.visualizer_app import main; print(main is not None)"`
预期：两者都通过。

### 任务 3：集成验证

**文件：**
- 修改：`docs/plan/v1-index.md`

- [ ] **步骤 1：运行全量测试**

运行：`python -m pytest`
预期：全部测试通过。

- [ ] **步骤 2：运行脚本帮助**

运行：`uv run --extra ble m5-visualizer --help`
预期：argparse 帮助输出并 exit code 0。

- [ ] **步骤 3：更新文档**

在 `docs/plan/v1-index.md` 中记录可视化命令和验证状态。
