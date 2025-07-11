#ifndef CONFIG_H
#define CONFIG_H

#include <QString>
#include <QStandardPaths>
#include <QDir>

namespace DesktopNotesConfig {

    inline QString getConfigDir() {
        QString path = QStandardPaths::writableLocation(QStandardPaths::AppConfigLocation);
        if (path.isEmpty()) { // Fallback for environments where AppConfigLocation might not be specific enough
            path = QDir::homePath() + "/.config/desktop-notes";
        } else if (!path.endsWith(QStringLiteral("/desktop-notes"))) {
             // QStandardPaths::AppConfigLocation usually includes org name and app name
             // For direct usage, we might append if not set by QCoreApplication organization/name
             // However, for plasmoids, this might be handled differently or inherited.
             // For now, assume it gives a base like ~/.config/ and we append our folder.
             // A better approach for plasmoids is to use KPackage structure.
             // Let's assume QStandardPaths gives something like ~/.config/yourappname
             // For now, we'll ensure our specific folder name.
            path = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation) + "/desktop-notes";
        }

        QDir dir(path);
        if (!dir.exists()) {
            dir.mkpath(".");
        }
        return path;
    }

    inline QString getDataDir() {
        QString path = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
         if (path.isEmpty()) {
            path = QDir::homePath() + "/.local/share/desktop-notes";
        } else if (!path.endsWith(QStringLiteral("/desktop-notes"))) {
            // Similar to above, ensuring our specific folder.
            path = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation) + "/desktop-notes";
        }

        QDir dir(path);
        if (!dir.exists()) {
            dir.mkpath(".");
        }
        return path;
    }

    inline QString getSettingsFilePath() {
        return getConfigDir() + "/settings.ini";
    }

    inline QString getDatabaseFilePath() {
        return getDataDir() + "/notes.db";
    }

    const QString PLASMOID_NAME = "org.kde.desktopnotes";

} // namespace DesktopNotesConfig

#endif // CONFIG_H
