#include "stylingdialog.h"
#include "desktopnotesapplet.h" // For applying style to applet

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QSlider>
#include <QPushButton>
#include <QSpinBox>
#include <QLabel>
#include <QColorDialog>
#include <QDialogButtonBox>
#include <QDebug>

StylingDialog::StylingDialog(DesktopNotesData::NoteStyle &currentStyle,
                               DesktopNotesApplet* targetApplet,
                               QWidget *parent)
    : QDialog(parent),
      m_currentStyleRef(currentStyle),
      m_originalStyle(currentStyle), // Make a copy for potential revert
      m_targetApplet(targetApplet)
{
    setWindowTitle(i18n("Note Styling"));
    setModal(true);

    setupUi();

    // Initialize controls with current style values
    m_transparencySlider->setValue(static_cast<int>(m_currentStyleRef.transparency * 100));
    m_transparencyValueLabel->setText(QString::number(m_currentStyleRef.transparency * 100) + "%");

    QColor initialColor(m_currentStyleRef.backgroundColor);
    m_colorPreviewLabel->setStyleSheet(QString("QLabel { background-color: %1; border: 1px solid black; }").arg(initialColor.name()));

    m_marginSlider->setValue(m_currentStyleRef.margin);
    m_marginSpinBox->setValue(m_currentStyleRef.margin);

    // Connections for real-time preview
    connect(m_transparencySlider, &QSlider::valueChanged, this, &StylingDialog::onTransparencyChanged);
    connect(m_marginSlider, &QSlider::valueChanged, this, &StylingDialog::onMarginChanged);
    connect(m_marginSpinBox, qOverload<int>(&QSpinBox::valueChanged), this, &StylingDialog::onMarginChanged); // For spinbox direct input
    connect(m_bgColorButton, &QPushButton::clicked, this, &StylingDialog::onChooseColorClicked);

    // Ok/Cancel buttons
    connect(m_okButton, &QPushButton::clicked, this, &StylingDialog::acceptDialog);
    connect(m_cancelButton, &QPushButton::clicked, this, &StylingDialog::rejectDialog);
}

StylingDialog::~StylingDialog()
{
    // Qt handles child widget deletion
}

void StylingDialog::setupUi()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);
    QFormLayout *formLayout = new QFormLayout();

    // --- Transparency ---
    m_transparencyLabel = new QLabel(i18n("Transparency:"));
    m_transparencySlider = new QSlider(Qt::Horizontal);
    m_transparencySlider->setRange(0, 100); // 0% to 100%
    m_transparencyValueLabel = new QLabel(); // To show percentage
    QHBoxLayout *transparencyLayout = new QHBoxLayout();
    transparencyLayout->addWidget(m_transparencySlider);
    transparencyLayout->addWidget(m_transparencyValueLabel);
    formLayout->addRow(m_transparencyLabel, transparencyLayout);

    // --- Background Color ---
    m_bgColorLabel = new QLabel(i18n("Background Color:"));
    m_bgColorButton = new QPushButton(i18n("Choose Color..."));
    m_colorPreviewLabel = new QLabel();
    m_colorPreviewLabel->setMinimumSize(50, 20); // Ensure it's visible
    m_colorPreviewLabel->setAutoFillBackground(true);
    QHBoxLayout *bgColorLayout = new QHBoxLayout();
    bgColorLayout->addWidget(m_bgColorButton);
    bgColorLayout->addWidget(m_colorPreviewLabel);
    bgColorLayout->addStretch();
    formLayout->addRow(m_bgColorLabel, bgColorLayout);

    // --- Margin ---
    m_marginLabel = new QLabel(i18n("Margin (pixels):"));
    m_marginSlider = new QSlider(Qt::Horizontal);
    m_marginSlider->setRange(0, 50); // Example range for margin
    m_marginSpinBox = new QSpinBox();
    m_marginSpinBox->setRange(0, 50);
    QHBoxLayout *marginLayout = new QHBoxLayout();
    marginLayout->addWidget(m_marginSlider);
    marginLayout->addWidget(m_marginSpinBox);
    formLayout->addRow(m_marginLabel, marginLayout);

    // Sync slider and spinbox for margin
    connect(m_marginSlider, &QSlider::valueChanged, m_marginSpinBox, &QSpinBox::setValue);
    connect(m_marginSpinBox, qOverload<int>(&QSpinBox::valueChanged), m_marginSlider, &QSlider::setValue);


    mainLayout->addLayout(formLayout);

    // --- Ok/Cancel Buttons ---
    QDialogButtonBox *buttonBox = new QDialogButtonBox();
    m_okButton = buttonBox->addButton(QDialogButtonBox::Ok);
    m_cancelButton = buttonBox->addButton(QDialogButtonBox::Cancel);
    mainLayout->addWidget(buttonBox);

    setLayout(mainLayout);
}

void StylingDialog::onTransparencyChanged(int value)
{
    m_currentStyleRef.transparency = static_cast<double>(value) / 100.0;
    m_transparencyValueLabel->setText(QString::number(value) + "%");
    if (m_targetApplet) {
        applyStyleToApplet(m_currentStyleRef);
    }
}

void StylingDialog::onMarginChanged(int value)
{
    m_currentStyleRef.margin = value;
    // If slider and spinbox are connected, one will update the other.
    // Ensure the styleRef is updated from the primary signal source or both.
    // Here, both slider and spinbox valueChanged signals are connected to this slot.
    // To avoid double application if one updates the other which then calls this again,
    // check if the value actually changed.
    // However, Qt's signal/slot usually handles this well unless we create a loop.
    // For simplicity, assume it works.
    if (m_marginSlider->value() != value) m_marginSlider->setValue(value);
    if (m_marginSpinBox->value() != value) m_marginSpinBox->setValue(value);

    if (m_targetApplet) {
        applyStyleToApplet(m_currentStyleRef);
    }
}

void StylingDialog::onChooseColorClicked()
{
    QColor currentColor = QColor(m_currentStyleRef.backgroundColor);
    QColorDialog colorDialog(currentColor, this);
    // Enable alpha selection if we want to support RGBA hex codes in the future,
    // but spec says hex #RRGGBB. Transparency is separate.
    // colorDialog.setOption(QColorDialog::ShowAlphaChannel, true);

    if (colorDialog.exec() == QDialog::Accepted) {
        QColor newColor = colorDialog.selectedColor();
        if (newColor.isValid()) {
            m_currentStyleRef.backgroundColor = newColor.name(QColor::HexRgb); // #RRGGBB format
            m_colorPreviewLabel->setStyleSheet(QString("QLabel { background-color: %1; border: 1px solid black; }").arg(newColor.name()));
            if (m_targetApplet) {
                applyStyleToApplet(m_currentStyleRef);
            }
        }
    }
}

void StylingDialog::applyStyleToApplet(const DesktopNotesData::NoteStyle& styleToApply)
{
    if (m_targetApplet) {
        // The applet needs a public method to temporarily apply a style for preview
        // or directly manipulate its visual properties based on the style struct.
        // For now, let's assume DesktopNotesApplet has a method:
        // m_targetApplet->previewStyle(styleToApply);
        // Or, more directly, if m_currentStyleRef is the applet's actual style object:
        m_targetApplet->applyNoteStyle(); // This will use the (already updated) m_currentStyleRef
        m_targetApplet->update(); // Ensure repaint
    }
}

DesktopNotesData::NoteStyle StylingDialog::getAppliedStyle() const
{
    // This is called if OK is pressed. The m_currentStyleRef has been updated throughout.
    return m_currentStyleRef;
}

DesktopNotesData::NoteStyle StylingDialog::getOriginalStyle() const
{
    // This is used if Cancel is pressed.
    return m_originalStyle;
}


void StylingDialog::acceptDialog()
{
    // m_currentStyleRef has already been updated with all changes.
    // No further action needed on the style object itself.
    // The caller (DesktopNotesApplet) will take m_currentStyleRef and save it.
    QDialog::accept();
}

void StylingDialog::rejectDialog()
{
    // Revert the m_currentStyleRef back to m_originalStyle
    m_currentStyleRef = m_originalStyle;
    // And apply this reversion to the applet for visual feedback
    if (m_targetApplet) {
        applyStyleToApplet(m_currentStyleRef); // Apply the original style back
    }
    QDialog::reject();
}

// In DesktopNotesApplet.h, we would need to add:
// friend class StylingDialog; // If StylingDialog needs to access private members for preview
// or add a public method:
// void previewStyle(const DesktopNotesData::NoteStyle& style);

// In DesktopNotesApplet.cpp's handleStyling():
// StylingDialog dialog(m_note.style, this, this); // Pass 'this' as parent and targetApplet
// if (dialog.exec() == QDialog::Accepted) {
//     // m_note.style is already updated by reference.
//     applyNoteStyle(); // Ensure final application (might be redundant if preview did it well)
//     saveNoteData();
// } else {
//     // m_note.style was reverted by dialog's rejectDialog().
//     // applyNoteStyle(); // Ensure final reversion (might be redundant)
// }

// For applyNoteStyle in DesktopNotesApplet to work with the live changes,
// m_currentStyleRef in StylingDialog must indeed be a reference to m_note.style in the applet.
// Then, DesktopNotesApplet::applyNoteStyle() will always use the latest values from the dialog.
// DesktopNotesApplet::update() should also be called by applyNoteStyle().
