# Text-to-SQL Multi-Agent System with Clarification Engine

An agentic Text-to-SQL system built using **LangGraph**, **Groq**, and **FastAPI**. It features an interactive **clarification loop** to eliminate ambiguity before query synthesis, a **schema pruning agent** to minimize token cost, a **dual-layer self-correcting validator**, and a plain-English **explanation agent**.

---

## 🌟 Key Highlights

- **Clarification Engine**: Detects ambiguous or underspecified queries (e.g., *"Who was the best customer last month?"*) and asks targeted questions (up to 3 retries) before attempting SQL generation.
- **Contextual Schema Pruning**: Instead of dumping the full schema, the Schema Agent extracts only relevant tables, columns, and relationships required for the query.
- **Self-Correcting SQL Validator**:
  - **Hard Rules**: Intercepts dangerous operations (`DROP`, `DELETE`, `UPDATE`, `ALTER`, etc.) and non-existent tables immediately.
  - **LLM Validator**: Validates semantic intent, correct `JOIN` keys, and detects expensive queries (e.g., unintended Cartesian/`CROSS JOIN`s).
  - Automatically feeds compiler/semantic error feedback back to the generator (up to 3 retries).
- **Execution Sandbox**: Executes strictly validated read-only SQL queries against PostgreSQL.
- **Plain-English Explanations**: Transforms tabular results into intuitive, business-friendly summaries.
- **Test Coverage**: Comprehensive test suite covering 18 test scenarios across 27 unit and integration tests.

---

## 🏗️ Architecture & Workflow

```
                        User Question
                              │
                              ▼
                   ┌─────────────────────┐
                   │  Intent/Ambiguity   │◄──────────────────────┐
                   │       Agent         │                       │
                   └──────────┬──────────┘                       │
                              │                                  │
                 ┌────────────┴────────────┐                     │
        Clear    │                         │ Unclear             │
                 ▼                         ▼                     │
       ┌───────────────────┐     ┌───────────────────┐           │
       │   Schema Agent    │     │   Clarification   │───────────┘
       │  (Prunes Schema)  │     │   (Max 3 Loops)   │
       └─────────┬─────────┘     └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
 ┌────►│   SQL Generator   │◄───────────────────────────┐
 │     │       Agent       │                            │
 │     └─────────┬─────────┘                            │
 │               │                                      │
 │               ▼                                      │
 │     ┌───────────────────┐                            │
 │     │   SQL Validator   │─── Issues (Max 3 Loops) ───┘
 │     │  (Safety + Intent)│
 │     └─────────┬─────────┘
 │               │ Valid
 │               ▼
 │     ┌───────────────────┐
 │     │  SQL Execution    │
 │     │    (Sandbox)      │
 │     └─────────┬─────────┘
 │               │
 │               ▼
 │     ┌───────────────────┐
 └─────┤ Explanation Agent │
       └─────────┬─────────┘
                 │
                 ▼
       Final Response to User
```

---

## 🛠️ Tech Stack

- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph)
- **LLM**: Groq (`openai/gpt-oss-120b` or `openai/gpt-oss-20b`) via `langchain-groq`
- **Database**: PostgreSQL 16 (via Docker or Cloud Serverless)
- **API Framework**: FastAPI + Uvicorn
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **Testing**: Pytest & Pytest-Asyncio (fully mocked offline test suite)
- **Containerization**: Docker & Docker Compose

---

## 🗄️ Database Schema

Synthetic e-commerce database with realistic orders spanning 18 months:

| Table | Description | Columns |
| :--- | :--- | :--- |
| `customers` | User profiles | `customer_id`, `name`, `email`, `city`, `created_at` |
| `categories` | Product departments | `category_id`, `name` |
| `products` | Product catalog | `product_id`, `name`, `category_id`, `price`, `stock` |
| `orders` | Customer purchases | `order_id`, `customer_id`, `status`, `ordered_at` |
| `order_items`| Order line items | `item_id`, `order_id`, `product_id`, `quantity`, `unit_price` |

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `winget install astral-sh.uv` on Windows)
- Docker Desktop

### 2. Clone and Setup Environment
```bash
git clone <your-repo-url>
cd text2sql

# Install all dependencies using uv
uv sync
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your credentials:
```env
GROQ_API_KEY=your_groq_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=postgres
```

### 4. Start the Database and Seed
```bash
# Start PostgreSQL container
docker compose up -d

# Seed the database with 300 orders across 18 months
uv run python db/seed.py
```

### 5. Start the FastAPI Server
```bash
uv run python main.py
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** to access the interactive Swagger API documentation.

---

## 📡 API Usage

### `POST /query`

**Request Body:**
```json
{
  "question": "Who was our best customer last month?"
}
```

**Response Body:**
```json
{
  "success": true,
  "final_answer": "Alice Johnson was the top customer last month, generating $1,248.50 across 3 orders.",
  "sql_query": "SELECT c.name, SUM(oi.quantity * oi.unit_price) AS total_spent FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id WHERE o.ordered_at >= NOW() - INTERVAL '30 days' GROUP BY c.name ORDER BY total_spent DESC LIMIT 1;",
  "query_result": [
    {
      "name": "Alice Johnson",
      "total_spent": 1248.50
    }
  ],
  "clarification_history": [
    {
      "agent_question": "Do you want to measure the best customer by total revenue spent or by number of orders placed?",
      "user_answer": "Total revenue spent."
    }
  ],
  "error_message": null
}
```

---

## 🧪 Running Tests

The test suite runs completely offline using mocks for LLM and database drivers:

```bash
uv run pytest tests/ -v
```

All **27 test cases** pass, validating:
- Unrelated query rejection (e.g. *"What is the capital of France?"*)
- Ambiguous query clarification loops and retry caps
- Defense against destructive queries (`DROP`, `DELETE`, `UPDATE`)
- Autonomous self-correction for invalid column names, wrong table names, and incorrect `JOIN` keys
- Detection and correction of Cartesian/expensive queries
- Safe handling of empty result sets and database connection errors

---

## 🚢 Deployment

### Free-Tier Cloud Deployment (Neon + Render)
1. **Database**: Create a free PostgreSQL instance on [Neon.tech](https://neon.tech) and run [db/schema.sql](file:///d:/Machine%20Learning/text2sql/db/schema.sql) in their SQL console.
2. **Backend**: Deploy this repository to [Render.com](https://render.com) as a Web Service using the provided [Dockerfile](file:///d:/Machine%20Learning/text2sql/Dockerfile).
3. Set `GROQ_API_KEY` and `DATABASE_URL` in Render's environment settings.

### Docker Compose (Self-Hosted VPS)
To deploy both backend and database on a single server:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```