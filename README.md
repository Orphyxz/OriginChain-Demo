# OriginChain

> AI-Powered Blockchain-Based Product Authentication System

OriginChain is a Final Year Engineering Project that aims to combat counterfeit products by combining **Blockchain**, **Artificial Intelligence**, and **Barcode Verification**. The system enables secure product registration, ownership tracking across the supply chain, and authenticity verification for consumers.

---

## 📖 Project Overview

Counterfeit products are a major challenge across industries such as pharmaceuticals, electronics, luxury goods, and consumer products. Traditional authentication methods can be forged or manipulated.

OriginChain addresses this problem by:

- Registering products on the blockchain
- Generating unique barcodes for every product unit
- Tracking ownership transfers throughout the supply chain
- Allowing consumers to verify product authenticity
- Using AI to analyze product packaging for additional counterfeit detection

---

## 🎯 Objectives

- Prevent counterfeit products
- Ensure end-to-end product traceability
- Provide transparent ownership history
- Enable secure product verification
- Integrate AI for packaging authenticity analysis

---

## 👥 Team Members

| Name | Role |
|------|------|
| Durva Waghchaure | Backend Lead & Project Lead |
| Aradhya | Frontend Lead |
| Aryan | Blockchain Lead |
| Purvika | AI Lead |

---

## 🛠️ Technology Stack

### Frontend
- Next.js
- React
- Tailwind CSS

### Backend
- FastAPI
- Python
- SQLAlchemy
- JWT Authentication

### Database
- PostgreSQL

### Blockchain
- Solidity
- Polygon
- Hardhat
- IPFS

### Artificial Intelligence
- OpenCV
- PyTorch
- Isolation Forest

---

## 🏗️ System Architecture

```
Frontend (Next.js)
        │
        ▼
Backend (FastAPI)
        │
 ┌──────┴────────┐
 ▼               ▼
PostgreSQL   Blockchain
                 │
                 ▼
              Polygon

        │
        ▼
AI Verification
(OpenCV + PyTorch)
```

---

## 📦 Project Structure

```
OriginChain/
│
├── frontend/         # Next.js application
├── backend/          # FastAPI application
├── blockchain/       # Smart contracts & Hardhat
├── ai/               # AI model & image processing
├── docs/             # Documentation
├── assets/           # Images and resources
├── README.md
└── LICENSE
```

---

## 🔄 Product Flow

```
Manufacturer
      │
      ▼
Create Product
      │
      ▼
Create Product Batch
      │
      ▼
Generate Product Units
      │
      ▼
Generate Unique Barcode
      │
      ▼
Register on Blockchain
      │
      ▼
Distributor
      │
      ▼
Retailer
      │
      ▼
Consumer
      │
      ▼
Barcode Verification
      │
      ▼
AI Packaging Verification (Optional)
```

---

## ✨ Key Features

- Secure user authentication using JWT
- Role-Based Access Control (RBAC)
- Product registration and management
- Batch and unit management
- Automatic barcode generation
- Blockchain-based authenticity records
- Ownership transfer tracking
- Consumer barcode verification
- AI-powered packaging verification
- Verification logs and audit trail
- Role-specific dashboards

---

## 📄 Documentation

Project documentation is available in the `docs/` directory.

- Software Requirements Specification (SRS)
- Database Design
- API Documentation
- UI Design
- Blockchain Design
- AI Design
- Meeting Notes
- Presentation

---

## 🚀 Current Status

**Project Phase:** Design & Planning

Completed:
- Project Planning
- Team Formation
- Architecture Design
- Software Requirements Specification (SRS)
- Database Design

Upcoming:
- API Design
- UI Wireframes
- Backend Development
- Frontend Development
- Blockchain Integration
- AI Model Development
- Testing & Deployment

---

## 📜 License

This project is developed for educational purposes as part of the Bachelor of Engineering (Computer Engineering) curriculum.
