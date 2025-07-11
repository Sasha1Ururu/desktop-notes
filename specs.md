# Desktop-notes
A simple app to display txt files (read-only) as desktop widgets in Plasma 6.


## Overview
Each instance can open one ".txt" or ".md" file or create a new one (in the same file selection dialog).
User configuration is stored at ~ (home) (where exactly?).
type note = {id: int, status: [shown, hidden], filepath: [None, Path]}


## Behaviour

### Quick Left-click to open file
if Note has filename:
"konsole edit $filename"
edit will run "nvim" in my case

if Note doesn't have filename yet:
open "File selection" dialog

### Left-click&Hold on Note to drag the widget

### Drag corners to resize

### Right-click on Note to evoke context menu
- Select file
- Hide
- Delete (doesn't delete the file, but only the Note in database)
- Open Notes (opens list of all Notes - hidden and shown. Columns are clickable - to sort. Click on "status" cell to flip status of the Note.)
- Styling (opens styling settings for the Note)

#### Styling
- Transparency (slider)
- Background color (opens color picker)
Note that any of settings change should have effect on the Note instantly - without the need to close current dialog or Apply settings.
- Ok & Cancel (buttons)
Ok = Apply & Exit
Cancel = Exit but revert settings to previous version


