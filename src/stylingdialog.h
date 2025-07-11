#ifndef STYLINGDIALOG_H
#define STYLINGDIALOG_H

#include <QDialog>
#include "data/notedata.h" // For NoteStyle struct

// Forward declarations
class QSlider;
class QPushButton;
class QSpinBox;
class QLabel;
class DesktopNotesApplet; // To apply styles in real-time

namespace Ui { // Standard Qt Designer practice, though we're doing it manually
class StylingDialog;
}

class StylingDialog : public QDialog
{
    Q_OBJECT

public:
    explicit StylingDialog(DesktopNotesData::NoteStyle& currentStyle,
                           DesktopNotesApplet* targetApplet, // For real-time preview
                           QWidget *parent = nullptr);
    ~StylingDialog();

    DesktopNotesData::NoteStyle getAppliedStyle() const;
    DesktopNotesData::NoteStyle getOriginalStyle() const;


private slots:
    void onTransparencyChanged(int value);
    void onMarginChanged(int value);
    void onChooseColorClicked();

    void acceptDialog(); // Ok
    void rejectDialog(); // Cancel

private:
    void setupUi();
    void applyStyleToApplet(const DesktopNotesData::NoteStyle& styleToApply); // Helper for preview

    DesktopNotesData::NoteStyle &m_currentStyleRef; // Reference to the style being edited
    DesktopNotesData::NoteStyle m_originalStyle;   // Copy of style when dialog opened, for Cancel
    DesktopNotesApplet* m_targetApplet;          // The applet instance to update for preview

    // UI Elements
    QLabel *m_transparencyLabel;
    QSlider *m_transparencySlider;
    QLabel *m_transparencyValueLabel;

    QLabel *m_bgColorLabel;
    QPushButton *m_bgColorButton;
    QLabel *m_colorPreviewLabel; // Shows the selected background color

    QLabel *m_marginLabel;
    QSlider *m_marginSlider;
    QSpinBox *m_marginSpinBox;

    QPushButton *m_okButton;
    QPushButton *m_cancelButton;
};

#endif // STYLINGDIALOG_H
