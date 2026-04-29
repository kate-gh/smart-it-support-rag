# Smart IT Support Assistant (RAG + AI)

An intelligent IT helpdesk chatbot esigned to automate technical support using **Retrieval-Augmented Generation (RAG)**.
The system combines **semantic search, LLM reasoning, and real-time learning** to deliver accurate and scalable IT assistance.

---

## Project Value

- Reduces manual IT support workload
- Provides instant responses to users
- Learns continuously from feedback
- Escalates unresolved issues into tickets
- Enables monitoring via an admin dashboard

---

## Features

- Intelligent chatbot (FR / EN)
- Knowledge base (ChromaDB → `vector_db/`)
- Auto-learning via Kafka
- Ticket management system
- Authentication (user / admin)
- Admin dashboard (React)

---

## Architecture

```text
Frontend (React)
        ↓
Flask API
        ↓
Controllers + AI Engine
        ↓
--------------------------------
| MySQL | ChromaDB | Kafka     |
--------------------------------
```

---

## Project Structure

```text
project/
├── app.py
├── it_agent.py
├── core/
│   ├── chat_controller.py
│   └── kb_controller.py
├── kafka_producer.py
├── kafka_consumer.py
├── users_store.py
├── tickets_store.py
├── pending_store.py
├── conversation_store.py
├── db.py
├── vector_db/          # ChromaDB storage (ignored)
├── it-chat/           # React app
├── scripts/
│   └── build_vectordb.py
└── .env                # environment variables

```

---

## Requirements

Before running the project, make sure you have:

- Python 3.10+
- MySQL installed and running
- Docker installed (for Kafka)

---

## Installation

```bash
git clone <repo-url>
cd project

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

---

## Environment Variables

Create `.env`:

```env
GROQ_API_KEY=your_api_key

MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=it_agent_db

SECRET_KEY=your_secret_key
```

---

## Database Setup

The MySQL database is **provided with the project (attached file)**

- Import it into MySQL
- Make sure the name matches `.env`

---

## Build Vector Database

```bash
python scripts/build_vectordb.py
```

---

## Kafka Setup (Docker)

This project uses **Redpanda (Kafka)** for real-time learning.

Start Kafka:

```bash
docker compose up -d
```

Kafka will run on:

```
localhost:9092
```

---

## Run Project

```bash
# Start backend
python app.py

# Start frontend
cd it-chat
npm install
npm run dev
```

Open: http://localhost:5173

---

## How It Works

```text
User → Chat → KB Search → LLM fallback → Feedback → Kafka → KB update
```

---

## Not Included

- `vector_db/`
- ML models
- datasets
- `.env`

---

## Tech Stack

- Flask
- MySQL
- ChromaDB
- Groq LLM
- Kafka (Redpanda)
- React

---

## License

MIT License

Copyright (c) 2026 KAWTAR GANTOUH
