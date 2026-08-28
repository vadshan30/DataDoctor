# 🏥 DataDoctor

**AI-Powered Automated Data Science & Machine Learning Platform**

DataDoctor is an end-to-end platform that automates the machine learning workflow — from dataset upload and data analysis to model training, evaluation, explainability, and report generation.

[![GitHub Release](https://img.shields.io/github/v/release/vadshan30/DataDoctor)](https://github.com/vadshan30/DataDoctor/releases/tag/v1.0.0)
[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18.6-336791.svg)](https://www.postgresql.org/)

---

## 🚀 Features

- 📊 **Dataset Upload** — CSV, XLSX, and XLS support
- 🔍 **Data Profiling** — Statistics, data types, missing values, and distributions
- ✅ **Quality Analysis** — Automated data quality score and recommendations
- 🧹 **Data Cleaning** — Missing-value handling, duplicate removal, and cleaning
- ⚡ **Feature Engineering** — Automated feature transformation and encoding
- 🎯 **ML Preparation** — Preprocessing, scaling, encoding, and leakage prevention
- 🧠 **Model Training** — Multiple machine learning algorithms
- 📈 **Model Evaluation** — Metrics, comparison, and best model selection
- 🔍 **Explainability** — SHAP-based feature importance
- 📄 **Reports** — Automated PDF/HTML reports with insights
- 🔐 **Authentication** — JWT, guest login, and password reset

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| **Backend** | Python, FastAPI, SQLAlchemy |
| **Frontend** | React, TypeScript, Tailwind CSS, Vite |
| **Database** | PostgreSQL 18.6 |
| **Machine Learning** | Scikit-learn, XGBoost, LightGBM, Optuna, SHAP |
| **Data Science** | Pandas, NumPy |
| **Email** | Resend API |
| **Infrastructure** | Docker, Docker Compose |
| **Migrations** | Alembic |

---

## 🔄 Workflow

```text
📊 Upload
   ↓
🔍 Profile
   ↓
✅ Quality Analysis
   ↓
🧹 Data Cleaning
   ↓
⚡ Feature Engineering
   ↓
🎯 ML Preparation
   ↓
🧠 Model Training
   ↓
📈 Evaluation
   ↓
🔍 Explainability
   ↓
📄 Report Generation
```

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────┐
│       React + TypeScript Frontend       │
│           Tailwind CSS UI               │
└──────────────────┬──────────────────────┘
                   │ HTTP / JWT
                   ↓
┌─────────────────────────────────────────┐
│             FastAPI Backend             │
│        REST API + Swagger Docs          │
└──────────────┬─────────┬─────────┬─────┘
               │         │         │
               ↓         ↓         ↓
          ┌────────┐ ┌────────┐ ┌────────┐
          │  Data  │ │   ML   │ │   AI   │
          │ Engine │ │ Engine │ │ Engine │
          └────┬───┘ └────┬───┘ └────┬───┘
               │           │           │
               └───────────┼───────────┘
                           ↓
                ┌───────────────────┐
                │   PostgreSQL 18.6 │
                │    + SQLAlchemy   │
                └───────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 18.6+
- Git

### 1. Clone Repository

```bash
git clone https://github.com/vadshan30/DataDoctor.git
cd DataDoctor
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
```

**Windows:**

```powershell
venv\Scripts\activate
```

**Linux/macOS:**

```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

Backend: `http://localhost:8000`

API Docs: `http://localhost:8000/docs`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest -v
```

**234+ tests passing**

### Frontend Build

```bash
cd frontend
npm run build
```

---

## 📁 Project Structure

```text
DataDoctor/
├── backend/
│   ├── app/
│   ├── migrations/
│   ├── tests/
│   ├── uploads/
│   ├── models/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── docker-compose.yml
├── README.md
└── LICENSE
```

---

## 🐳 Docker

```bash
docker-compose up -d --build
```

To stop services:

```bash
docker-compose down
```

---

## 📊 Project Status

- ✅ End-to-end data science pipeline
- ✅ 234+ backend tests passing
- ✅ React frontend
- ✅ FastAPI backend
- ✅ PostgreSQL database
- ✅ Authentication system
- ✅ Machine learning pipeline
- ✅ SHAP explainability
- ✅ Automated reports
- ✅ Docker support

---

## 📝 License

This project is for educational purposes as part of a 3rd-year engineering project.

---

## ⭐ Support

If you find DataDoctor useful, please ⭐ **Star this repository**.

**Project:** https://github.com/vadshan30/DataDoctor

Made with ❤️ for the Data Science community.
