
# Intelligent Real Estate Assistant 🏠

This project is a full-stack web application designed to serve as an all-in-one management tool for real estate agents. It replaces traditional Excel-based workflows with a modern, database-driven application featuring an AI-powered recommendation engine and a complete client management system.

The application is built with a **FastAPI** backend to handle data logic and a **Streamlit** multi-page frontend for a user-friendly, interactive experience.

---

## ✨ Features

This application provides a comprehensive suite of tools for real estate agents:

* **🏠 Main Dashboard:** An "At a Glance" homepage showing key metrics like total clients, active listings, and client needs.
* **🤝 AI Recommendation Engine:** Select any client to instantly receive a list of the top matching properties from the database. The engine uses a smart fallback system, first searching by location and then expanding the search if no perfect matches are found.
* **📈 Full Client Management (CRUD):** A dedicated page with a modern tabbed interface to:
  * **Create:** Add new clients to the database through a simple form.
  * **Read:** View all client details and requirements.
  * **Update:** Edit existing client information.
  * **Delete:** Safely remove clients with a confirmation step.
* **🏘️ Interactive Property Explorer:** A powerful dashboard to browse, search, and filter the entire property inventory by listing type, property type, location, and price range.
* **📅 Task Management:** Add, view, and update tasks/events for clients, such as site visits and negotiations, with automatic client status updates.
* **📊 Market Analysis:** (If implemented) Tools for property price prediction and data visualization.
* **Testing:** Comprehensive unit tests for utility functions using pytest to ensure reliability.

---

## 🛠️ Tech Stack

This project leverages a modern Python-based stack for data science and web development:

* **Backend:**
  * **FastAPI:** For creating a high-performance, robust REST API.
  * **Uvicorn:** As the ASGI server to run the FastAPI application.
* **Frontend:**
  * **Streamlit:** For building a beautiful, interactive multi-page user interface purely in Python.
* **Data & ML:**
  * **Pandas:** For all data manipulation and preparation tasks.
  * **Scikit-learn:** For machine learning model training and evaluation (used for the price prediction model prototype).
  * **Joblib:** For model serialization.
* **Database:**
  * **SQLite:** As a lightweight, file-based database.
* **Other:**
  * **Requests:** For handling external API calls (e.g., image fetching).
  * **FPDF:** For generating PDF reports.
  * **Pytest:** For unit testing.

---

## 🚀 How to Run Locally

To run this project on your local machine, please follow these steps:

1. **Clone the Repository:**
   ```bash
   git clone [your-repository-url]
   cd [your-repository-folder]
   ```
