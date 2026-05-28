cmake_minimum_required(VERSION 3.18)
project(marrow_embed_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compile the marrow core directly into this binary so the demo is
# self-contained: no install step, no library hunting. In a real
# downstream project you would either build marrow as a shared
# library and link to it, or vendor src/core/ as a git submodule.
get_filename_component(MARROW_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)

add_executable(marrow_embed_demo
    main.cpp
    ${MARROW_ROOT}/src/core/engine.cpp
)
target_include_directories(marrow_embed_demo
    PRIVATE ${MARROW_ROOT}/src/core)

if(NOT MSVC)
    target_compile_options(marrow_embed_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()
