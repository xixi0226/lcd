cmake_minimum_required(VERSION 2.8.3)
project(line_clustering)

add_definitions(-std=c++11)

find_package(catkin_simple REQUIRED)
catkin_simple(ALL_DEPS_REQUIRED)

cs_add_library(${PROJECT_NAME}
  src/line_clustering.cc
)

add_custom_target(test_data)
add_custom_command(TARGET test_data
                   COMMAND rm -rf test_data
                   COMMAND mkdir -p test_data
                   COMMAND cp -r ${CMAKE_SOURCE_DIR}/../test_data/line_clustering/*
                                 test_data/ || :)

catkin_add_gtest(test_line_clustering test/test_line_clustering.cc)
target_link_libraries(test_line_clustering ${PROJECT_NAME} pthread)
add_dependencies(test_line_clustering test_data)

cs_install()
cs_export()
