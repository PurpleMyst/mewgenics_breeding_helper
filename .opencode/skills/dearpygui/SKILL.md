---
name: dearpygui-autonomous-agent
description: Comprehensive operational guidelines for an OpenCode agent to autonomously write, execute, and debug modern DearPyGui (1.x) applications.
license: MIT
compatibility: opencode
metadata:
  environment: windows-11
  target_library: dearpygui>=1.0.0
---

# OpenCode Agent Skill: Autonomous DearPyGui 1.x Developer

## 🎯 Primary Directive
You are an autonomous OpenCode software agent tasked with building and maintaining graphical interfaces using **DearPyGui (DPG) version 1.x**. 

**Crucial Context:** You are operating directly within the file system. **Do not** output conversational code blocks expecting the user to copy and paste them into their editor (Neovim). You must write to the files yourself, execute them via PowerShell Core to verify they do not crash on initialization, and iteratively fix your own bugs.

Your training data is highly polluted with deprecated DPG 0.8 syntax. You must actively suppress legacy patterns and strictly adhere to the 1.x architecture defined below.

---

## 🏗️ 1. The DPG 1.x Architecture (Zero Exceptions)

Every DPG application you write or modify must strictly follow this lifecycle. Failure to initialize the context before creating UI elements will result in fatal internal stack crashes.

```python
import dearpygui.dearpygui as dpg

def main():
    # 1. INIT: Must be the absolute first DPG call
    dpg.create_context() 

    # 2. BUILD: Define UI elements using context managers and string tags
    with dpg.window(tag="primary_window", label="Main Application"):
        dpg.add_text("System Ready.", tag="status_text")
        # Do not use legacy add_spacing or add_same_line
        with dpg.group(horizontal=True):
            dpg.add_button(label="Action", callback=my_callback)

    # 3. SETUP: Create viewport and prepare render
    dpg.create_viewport(title="Application", width=1024, height=768)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    # Optional but common: Bind the main window to fill the viewport
    dpg.set_primary_window("primary_window", True)
    
    # 4. EXECUTE: Start the blocking render loop
    dpg.start_dearpygui()
    
    # 5. CLEANUP: Must occur after the window is closed
    dpg.destroy_context()

if __name__ == "__main__":
    main()

```

---

## 🛡️ 2. The Anti-Hallucination Translation Matrix

When generating code, you will naturally gravitate toward deprecated 0.8 parameters. You must run an internal check against this matrix before writing to the file.

**Tables & Layouts:**

* ❌ `row_bg=True` ➔ ✅ `row_background=True`
* ❌ `borders_inner=True` ➔ ✅ `borders_innerH=True, borders_innerV=True`
* ❌ `borders_outer=True` ➔ ✅ `borders_outerH=True, borders_outerV=True`
* ❌ `sort=True` ➔ ✅ `sortable=True`
* ❌ passing a `data` array to a table ➔ ✅ tables take no data; rows must be populated dynamically inside a `with dpg.table_row():` context manager.
* ❌ `name="MyWindow"` ➔ ✅ `label="MyWindow"` (for display) and `tag="unique_id"` (for programmatic reference).

---

## 🔄 3. State Management & Callbacks

As an agent working on systems-level tools, you must handle state cleanly. All callbacks in DPG 1.x strictly require a three-argument signature.

```python
def system_callback(sender, app_data, user_data):
    """
    sender: The string tag (or integer ID) of the widget that triggered this.
    app_data: The widget's payload (e.g., file path from a dialog, boolean from checkbox).
    user_data: Arbitrary data passed when the callback was registered.
    """
    # Always update UI state using the string tag
    dpg.set_value("status_text", f"Action triggered by {sender}")

```

---

## 🛠️ 4. Autonomous Execution & Debugging Protocol

Because you are executing code autonomously, GUI programming presents unique challenges. Follow this execution loop:

1. **Write/Modify:** Update the `.py` files directly using standard string tags for all UI elements to ensure easy retrieval and modification.
2. **Execute to Verify:** Run the script using PowerShell Core (`python script.py`).
3. **Handle Context Crashes:** If the script crashes immediately with `SystemError` or `Exception: Error: [1009] Message: No container to pop`, **do not panic**.
* *Root Cause:* This specifically means you passed an invalid/deprecated keyword argument (like `borders_inner`) to a widget inside a context manager (like `with dpg.table():`).
* *Resolution:* The DPG stack corrupted and failed to close. Review your newly written widget against the Translation Matrix, fix the incorrect parameter, and re-execute.
4. **Handoff:** Because you cannot "see" the GUI or click the buttons, once the application runs without throwing initialization errors in the terminal, stop execution and ask the user to test the visual layout and interaction.
