cmake_minimum_required(VERSION 2.8.12)
project(test)

# 添加子目录，目录下必须有CMakeLists.txt
#add_subdirectory(dlib test_build)

add_executable(test test.cpp)

# 项目依赖静态库
#target_link_libraries(test dlib::dlib)