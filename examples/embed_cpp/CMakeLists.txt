cmake_minimum_required(VERSION 3.18)
project(agentcore_embed_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compile the agentcore core directly into this binary so the demo is
# self-contained: no install step, no library hunting. In a real
# downstream project you would either build agentcore as a shared
# library and link to it, or vendor src/core/ as a git submodule.
get_filename_component(AGENTCORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)

add_executable(agentcore_embed_demo
    main.cpp
    ${AGENTCORE_ROOT}/src/core/engine.cpp
)
target_include_directories(agentcore_embed_demo
    PRIVATE ${AGENTCORE_ROOT}/src/core)

if(NOT MSVC)
    target_compile_options(agentcore_embed_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()
