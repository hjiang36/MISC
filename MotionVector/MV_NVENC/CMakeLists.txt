cmake_minimum_required(VERSION 3.13)
project(mv_nvenc VERSION 1.0.0 LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)

# Find CUDA
find_package(CUDA)
message("CUDA_CUDA_LIBRARY: ${CUDA_CUDA_LIBRARY}")
message("CUDA_TOOLKIT_ROOT_DIR: ${CUDA_TOOLKIT_ROOT_DIR}")

set(CUDA_HOST_COMPILER ${CMAKE_CXX_COMPILER})

# NVEncode
set(NVENCODEAPI_LIB ${CMAKE_CURRENT_SOURCE_DIR}/third_party/NVENC/Lib/x64/nvencodeapi.lib)
set(NVENCODEAPI_INCLUDE "third_party/NVENC/Interface")

# Stb image
set(STB_IMAGE_INCLUDE "third_party/stb")

# Add source files
set(SOURCE_FILE main.cpp)

# Create binary
add_executable(${PROJECT_NAME} ${SOURCE_FILE})
target_include_directories(${PROJECT_NAME} PUBLIC 
    ${CUDA_INCLUDE_DIRS}
    ${NVENCODEAPI_INCLUDE}
    ${STB_IMAGE_INCLUDE}
)
target_link_libraries(${PROJECT_NAME} ${CUDA_CUDA_LIBRARY} ${NVENCODEAPI_LIB})
