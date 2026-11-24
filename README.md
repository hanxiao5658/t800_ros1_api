# t800_ros1_api

用于 **Docker1 / ROS Noetic / Python 3.8** 的简易 FastAPI + Uvicorn 服务网关，不修改原有定位与导航节点。请求体均为 `{}`，四个 ROS Service 均使用标准 `std_srvs/Trigger`。

## HTTP API

| HTTP POST | ROS1 Service | 功能 |
| --- | --- | --- |
| `/api/v1/my_ros1/localization/relocalize` | `/my_ros1/localization/relocalize` | FastGICP 重定位 |
| `/api/v1/my_ros1/navigation/start` | `/my_ros1/navigation/start` | 请求启动导航 |
| `/api/v1/my_ros1/navigation/pause` | `/my_ros1/navigation/pause` | 暂停导航 |
| `/api/v1/my_ros1/navigation/next_waypoint` | `/my_ros1/navigation/next_waypoint` | 前往下个 waypoint |

附加 `GET /health` 检查 HTTP 进程。浏览器交互式文档：`http://127.0.0.1:8000/docs`。

## Docker1 安装

将压缩包里的 `t800_ros1_api` 文件夹放到 `~/catkin_ws/src/`，在 Docker1 终端执行：

```bash
source /opt/ros/noetic/setup.bash
python3 -m pip install -r ~/catkin_ws/src/t800_ros1_api/requirements.txt
cd ~/catkin_ws
catkin_make
source ~/catkin_ws/devel/setup.bash
```

已经由 Docker1 配置的 `/opt/fastlio_ws/devel/setup.bash` 及 ROS 网络变量仍须沿用。`rospy`、`std_srvs` 通过 ROS Noetic 提供，**不要用 pip 安装**。

## 启动

先确保 `roscore` 和定位、导航节点运行并注册对应 ROS Service，再启动 API：

```bash
rosservice list | grep /my_ros1/
rosrun t800_ros1_api api_server.py
```

服务器只监听 `127.0.0.1:8000`，不会在 `start_robot.sh` 里自动启动。

## 调用示例

健康检查（无机器人动作）：

```bash
curl http://127.0.0.1:8000/health
```

**请在机器人安全静止时测试重定位：**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/my_ros1/localization/relocalize \
  -H 'Content-Type: application/json' \
  -d '{}'
```

**下面三项会改变机器人导航状态，仅在确保机器人安全后测试：**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/my_ros1/navigation/start -d '{}'
curl -X POST http://127.0.0.1:8000/api/v1/my_ros1/navigation/pause -d '{}'
curl -X POST http://127.0.0.1:8000/api/v1/my_ros1/navigation/next_waypoint -d '{}'
```

正常返回示例：

```json
{"service":"/my_ros1/navigation/start","success":false,"message":"Localization not ready: ..."}
```

**HTTP 200 并不等于导航操作成功**；请检查 JSON 的 `success`。`message` 保持原 ROS Service 返回的信息。

## 错误与安全约定

| HTTP 状态 | 说明 |
| --- | --- |
| 200 | ROS Service 正常回复；成功与否看 `success` |
| 409 | 前一个 ROS Service 还在调用，拒绝并发请求 |
| 503 | 等待 3 秒仍未发现 ROS Service |
| 502 | ROS Service 网络通信或调用失败 |

- 这里只为 **等待 ROS Service 注册** 设置 3 秒超时，**不**强行取消已发给 ROS 的指令。FastGICP 重定位可能持续数秒甚至更久，HTTP 客户端超时后请核实状态，切勿自动重试。
- `127.0.0.1` 默认仅本机可访问。在 Docker1 使用 `--network host` 的条件下，Jetson 宿主机及相同网络命名空间的容器可以调用它。
- 当前没有 HTTP 身份认证，**不要修改为 `0.0.0.0` 直接暴露到 Wi-Fi**。后续网页功能建议通过本机后端代理调用，并加鉴权、操作确认与日志记录。
- 原 `waypoint_controller.py` 的定位健康、障碍物和故障锁检查完全保留。本 API 不提供任何绕过安全检查的功能。
