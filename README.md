# 📝 Task Manager with Subtasks (Hierarchical Task Tracker)

This is a simple, browser-based tool designed to help you organize your projects by allowing tasks to be nested under one another. It's built with Python (Flask) for handling data and uses a simple interface for viewing and managing your tasks.

## ✨ Key Features You'll Use

* **Nested Tasks:** Easily create subtasks under any active main task to break down large goals.
* **Collapsible Views:** Click the arrow next to a parent task to quickly hide or show all its subtasks, simplifying complex lists.
* **Filtered Views:** Quickly switch between three views:
    * **🟢 Active Tasks:** Shows only tasks currently in progress.
    * **🟠 Non-Clear Tasks:** Shows all active, completed, or abandoned tasks (everything except cleared).
    * **⚪ All Tasks:** Shows every task, regardless of status.
* **Quick Actions:** Dedicated tabs for **Creating Tasks** and **Updating Status** appear on demand, keeping the main task list clean.
* **Data Integrity:** You can only assign a subtask to a parent that is currently marked as **ACTIVE**.

---

## 🚀 Getting Started

You only need Python installed to run this application.

### 1. Prerequisites

Make sure you have **Python 3** installed.

### 2. Setup

1.  **Gather Files:** Ensure the two main files (`server.py` and `templates/index.html`) are in the same project directory.
2.  **Install Flask:** Open your terminal in the project directory and install the necessary library:
    ```bash
    pip install Flask
    ```

### 3. Running the App

1.  In your terminal, start the server:
    ```bash
    python server.py
    ```
2.  The server automatically creates a file named `tasks.db` to save your data.
3.  Open your web browser and go to the address:
    ```
    [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
    ```

---

### Viewing and Organizing Tasks

| Element | Action | Result |
| :--- | :--- | :--- |
| **View Tabs** (Active, Non-Clear, All) | Click to switch | Refreshes the list to show only tasks matching that filter. (Uses caching for speed!) |
| **`▼` / `▶` Icon** | Click next to any task | Collapses or expands all descendants of that task. |
| **Task Status** | Visible on the right | Color-coded status (`ACTIVE`, `COMPLETED`, `ABANDONED`, `CLEAR`) for quick identification. |

### Creating and Updating Tasks

1.  **Click on Button:** Click **➕ Create Task** or **🔄 Update Status** in the top-right corner. The input form will appear below the header. Clicking an active tab hides the form again.
2.  **Create Task Form:**
    * Enter a **Description**.
    * To make it a subtask, enter the **ID of an ACTIVE parent task** in the optional field.
3.  **Update Status Form:**
    * Enter the **ID** of the task you want to modify.
    * Select the **New Status** from the dropdown menu.
4.  **Feedback:** A short message (**Toast**) will pop up in the middle of the screen to confirm success or failure. The task list will automatically refresh.

---

## 🗑️ How to Reset Data

If you need to start completely fresh, simply stop the running server (using `Ctrl+C` in the terminal) and delete the data file:

1.  Stop the server.
2.  Delete the file named **`tasks.db`**.
3.  Restart the server (`python server.py`). A new, empty `tasks.db` file will be created.