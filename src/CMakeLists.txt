set(PROJECT_SRCS
    desktopnotesapplet.cpp
    data/databasemanager.cpp
    stylingdialog.cpp
    allnotesdialog.cpp
    # main.cpp # Add if we create a separate executable/service
)

set(PROJECT_HEADERS
    desktopnotesapplet.h
    config.h
    data/notedata.h
    data/databasemanager.h
    stylingdialog.h
    allnotesdialog.h
)

# Create a shared library for the plasmoid plugin
add_library(desktopnotesplugin MODULE ${PROJECT_SRCS} ${PROJECT_HEADERS})

target_link_libraries(desktopnotesplugin
    PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    # Qt6::Qml
    # Qt6::Quick
    KF6::Plasma
    KF6::Plasma5Support # For KDeclarative::ConfigPropertyMap if needed, or other compatibility
    KF6::I18n
    KF6::ConfigCore
    KF6::KIO
    KF6::CoreAddons
)

# For Plasma 6, plugin name usually follows reverse domain notation
set_target_properties(desktopnotesplugin PROPERTIES PREFIX "")
set_target_properties(desktopnotesplugin PROPERTIES OUTPUT_NAME "plasma_applet_org_kde_desktopnotes")


# Installation of the plugin
# The destination path might vary slightly based on system configuration
# Using KDE_INSTALL_PLUGINDIR for KF6/Plasma6 is preferred
include(KDEInstallDirs)
install(TARGETS desktopnotesplugin
    LIBRARY DESTINATION ${KDE_INSTALL_PLUGINDIR_KF6}/plasma/applets/
    MODULE DESTINATION ${KDE_INSTALL_PLUGINDIR_KF6}/plasma/applets/
)

# If you have QML files, they would be handled by kpackage structure
# and potentially installed via CMake as well.

# Add include directories
target_include_directories(desktopnotesplugin PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

message(STATUS "src/CMakeLists.txt configured for applet plugin.")
