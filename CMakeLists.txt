cmake_minimum_required(VERSION 3.16)
project(DesktopNotes VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Qml Quick)
find_package(KF6 REQUIRED COMPONENTS Plasma Plasma5Support I18n ConfigCore KIO CoreAddons) # Using KF6

# Define project source and header files
set(PROJECT_NAME "desktopnotes")

# Include subdirectory for the main applet source code
add_subdirectory(src)

# KDE Plasmara applet installation
# The actual installation might be more complex and involve kpackagetool6
# This is a simplified placeholder for where installation rules would go.
# Typically, this involves installing the .desktop file (or metadata.json for Plasma 6)
# and the plugin library to the correct Plasma directories.

# Example for Plasma 6 metadata.json (usually part of kpackage)
install(FILES
    package/metadata.json
    DESTINATION ${CMAKE_INSTALL_PREFIX}/share/plasma/plasmoids/org.kde.desktopnotes
)

# Note: More specific installation rules for the compiled plugin library
# (e.g., libdesktopnotesplugin.so) will be in src/CMakeLists.txt
# and will target something like:
# ${CMAKE_INSTALL_PREFIX}/lib/qt6/plugins/plasma/applets/
# or ${KDE_INSTALL_PLUGINDIR_KF6}/plasma/applets/

message(STATUS "Qt6_DIR: ${Qt6_DIR}")
message(STATUS "KF6_DIR: ${KF6_DIR}")

# Enable C++20 if needed and available, otherwise stick to C++17
# include(CheckCXXCompilerFlag)
# CHECK_CXX_COMPILER_FLAG("-std=c++2a" COMPILER_SUPPORTS_CXX2A)
# CHECK_CXX_COMPILER_FLAG("-std=c++20" COMPILER_SUPPORTS_CXX20)
# if(COMPILER_SUPPORTS_CXX2A)
#     set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++2a")
# elseif(COMPILER_SUPPORTS_CXX20)
#     set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++20")
# endif()

message(STATUS "DesktopNotes project configured.")
