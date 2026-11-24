#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T800 ROS1 Service 的 FastAPI 网关。

Docker1 / ROS Noetic / Python 3.8。
只允许访问下面列出的四个 std_srvs/Trigger Service。
启动方式：rosrun t800_ros1_api api_server.py
"""

import threading

import rospy
import uvicorn
from fastapi import FastAPI, HTTPException
from std_srvs.srv import Trigger, TriggerRequest


# HTTP 路径固定为 /api/v1 + ROS Service 的完整名称。
RELOCALIZE = "/my_ros1/localization/relocalize"
NAV_START = "/my_ros1/navigation/start"
NAV_PAUSE = "/my_ros1/navigation/pause"
NAV_NEXT = "/my_ros1/navigation/next_waypoint"

# 只限制等待服务“出现”的时间，不强行终止服务执行。
SERVICE_WAIT_TIMEOUT = 3.0

# 机器人操作接口串行处理，避免重定位/启停/换点的并发指令。
_service_lock = threading.Lock()

app = FastAPI(
    title="T800 ROS1 API",
    description="ROS1 定位与导航服务的 HTTP 封装；仅监听本机",
    version="0.1.0",
)


def call_trigger(service_name):
    """调用 ROS1 Trigger；success/message 原样传递，不重试控制指令。

    HTTP 200 仅表示 ROS Service 正常返回，操作是否成功看 JSON.success。
    """
    if not _service_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="另一个 ROS Service 请求正在执行；请勿重复发送机器人控制命令",
        )

    try:
        try:
            rospy.wait_for_service(service_name, timeout=SERVICE_WAIT_TIMEOUT)
        except (rospy.ROSException, rospy.ROSInterruptException) as exc:
            raise HTTPException(
                status_code=503,
                detail="ROS Service 不可用：{} ({})".format(service_name, exc),
            )

        try:
            # 每次重新连接，ROS 节点重启后不复用失效的持久连接。
            proxy = rospy.ServiceProxy(service_name, Trigger, persistent=False)
            result = proxy(TriggerRequest())
        except (rospy.ServiceException, rospy.ROSException) as exc:
            raise HTTPException(
                status_code=502,
                detail="ROS Service 调用失败：{} ({})".format(service_name, exc),
            )

        return {
            "service": service_name,
            "success": bool(result.success),
            "message": str(result.message),
        }
    finally:
        _service_lock.release()


@app.get("/health", summary="HTTP 进程健康检查")
def health():
    """API 进程存活不代表定位、导航节点正常。"""
    return {"status": "ok", "name": "t800_ros1_api"}


@app.post("/api/v1/my_ros1/localization/relocalize", summary="FastGICP 重定位")
def relocalize():
    """按定位仓库的现有逻辑执行一次重定位。"""
    return call_trigger(RELOCALIZE)


@app.post("/api/v1/my_ros1/navigation/start", summary="申请启动导航")
def navigation_start():
    """定位/障碍物/故障锁检查仍由 waypoint_controller 完成。"""
    return call_trigger(NAV_START)


@app.post("/api/v1/my_ros1/navigation/pause", summary="暂停导航")
def navigation_pause():
    """由原导航服务输出零速度，保留现有安全锁。"""
    return call_trigger(NAV_PAUSE)


@app.post("/api/v1/my_ros1/navigation/next_waypoint", summary="前往下一个 waypoint")
def navigation_next_waypoint():
    """是否允许下一点由原控制器决定，不跳过其状态检查。"""
    return call_trigger(NAV_NEXT)


def main():
    # Uvicorn 负责信号处理；不能使用多个 Worker 或 reload。
    rospy.init_node("t800_ros1_api", anonymous=False, disable_signals=True)
    rospy.loginfo("T800 ROS1 API: http://127.0.0.1:8000")

    # 控制机器人运动的接口尚无身份认证，严禁直接对外监听 0.0.0.0。
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    rospy.signal_shutdown("HTTP API stopped")


if __name__ == "__main__":
    main()
