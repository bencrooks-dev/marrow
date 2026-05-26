cmake_minimum_required(VERSION 3.18)
project(agentcore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(pybind11 CONFIG REQUIRED)

add_library(agentcore_core STATIC src/core/engine.cpp)
target_include_directories(agentcore_core PUBLIC src/core)
set_target_properties(agentcore_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

pybind11_add_module(_agentcore src/bindings/bindings.cpp)
target_link_libraries(_agentcore PRIVATE agentcore_core)
target_include_directories(_agentcore PRIVATE src/core)

install(TARGETS _agentcore LIBRARY DESTINATION agentcore)
