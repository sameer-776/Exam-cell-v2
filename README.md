# Poornima University - Exam Cell Notification Portal

A dynamic web application built with Python and Flask that serves as a central hub for all exam-related notifications at Poornima University. The portal features a sleek, user-facing website and a secure, full-featured admin panel for content management.

## ✨ Features

- **Dynamic Front-End:** A modern, responsive user interface built with HTML, CSS, and vanilla JavaScript.
- **Personalized Content:** Users can filter notifications by their specific department and academic year.
- **Dynamic Urgency:** Notification strips automatically change color (yellow/red) as deadlines approach.
- **Secure Admin Panel:** A password-protected dashboard for managing all site content, accessible at `/admin`.
- **Full Notification Management (CRUD):**
    - Create, edit, and delete notifications.
    - Attach files by either uploading a document or providing a URL.
    - Set notifications to be permanent or timed with specific start and end dates.
    - Automatically archives expired notifications.
- **Editable Quick Links:** The four main "Quick Access" cards on the homepage are fully editable from the admin panel.

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML5, CSS3, JavaScript
- **Database:** JSON files for simple, file-based data storage.

## 📂 Folder Structure

poornima_exam_portal/
│
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── admin_style.css
│   ├── images/
│   │   ├── logo.png
│   │   └── back.png
│   ├── js/
│   │   └── script.js
│   └── uploads/              # <-- NEW: For file uploads
│       └── (uploaded files will go here)
│
├── templates/
│   ├── index.html
│   ├── admin.html
│   └── login.html
│
├── app.py                    # The main application (heavily updated)
├── notifications.json        # Your notifications database
├── site_config.json          # For Quick Access links
└── users.json                # For admin credentials

## 🚀 Getting Started

Follow these instructions to get the project running on your local machine.

### Prerequisites

- Python 3.6+
- pip (Python package installer)

### Installation & Setup

1.  **Clone or download the repository.**
2.  **Navigate to the project directory:**
    ```bash
    cd poornima_exam_portal
    ```
3.  **(Recommended) Create and activate a virtual environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    venv\Scripts\activate
    ```
4.  **Install the required dependencies:**
    ```bash
    pip install Flask
    ```
5.  **Configure Admin Credentials:**
    The default admin login is stored in `users.json`.
    -   **Username:** `admin`
    -   **Password:** `password123`

### Running the Application

1.  **Run the Flask server:**
    ```bash
    python app.py
    ```
2.  **Access the portals in your browser:**
    -   **Main Website:** [http://localhost:5000](http://localhost:5000)
    -   **Admin Panel:** [http://localhost:5000/admin](http://localhost:5000/admin)

## 👥 Created By

This project was developed by **Team Shunya**:
- Sameer Beniwal
- Kshitij Soni
- Aryan Gaikwad
- Mohit Kumar

Under the supervision of Dr. Vipin Khattri.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for details.
