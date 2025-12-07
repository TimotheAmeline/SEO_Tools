## 🧠 LLM Visibility Tracker

Track your brand’s presence, sentiment, and ranking in responses from major LLMs (OpenAI, Gemini, etc.) using prompts you define—no overpriced SaaS required.

---

### 🚀 Features

* Upload a CSV of prompts or use previous prompts
* Toggle which chatbots to test (OpenAI, Gemini, Claude)
* Analyze each response for:
  * Brand mention
  * Sentiment (positive, neutral, negative)
  * Position/rank (if in a list)
* View historical performance
* Download results as CSV
* Console logs for live feedback

---

### 🛠 Setup

#### 1. Clone the project and create structure

Run this terminal command:

```bash
mkdir -p llm_tracker/{logs,data} && \
touch llm_tracker/{app.py,runner.py,chatbot_client.py,analyzer.py,history_manager.py,logger.py,requirements.txt} && \
touch llm_tracker/logs/.gitkeep && \
touch llm_tracker/data/.gitkeep
```

Then paste in the Python files I gave you.

---

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

#### 3. Set your API keys

```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."
```

For now, only OpenAI and Gemini are implemented.

---

#### 4. Run the app

```bash
streamlit run llm_tracker/app.py
```

---

### 📁 Files

| File                 | Purpose                                  |
| -------------------- | ---------------------------------------- |
| `app.py`             | Streamlit web UI                         |
| `runner.py`          | Main loop over prompts/platforms         |
| `chatbot_client.py`  | Chatbot API logic                        |
| `analyzer.py`        | Brand mention, sentiment, rank detection |
| `logger.py`          | Terminal logs                            |
| `history_manager.py` | Save/load results to local JSON          |
| `requirements.txt`   | Python dependencies                      |
| `data/`              | Stores prompt input/output files         |
| `logs/`              | Raw responses (can be extended)          |

---

### 📌 Prompt CSV Format

```csv
prompt
Who are the best contract automation tools?
What are the top SEO tools for enterprise websites?
List the most recommended CRM platforms for small businesses.
```

> **Important:** Header must be `prompt`.