cmake_minimum_required(VERSION 3.0.2)
project(t800_ros1_api)

find_package(catkin REQUIRED COMPONENTS rospy std_srvs)
catkin_package(CATKIN_DEPENDS rospy std_srvs)

# 允许用 rosrun t800_ros1_api api_server.py 启动
catkin_install_python(PROGRAMS scripts/api_server.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
