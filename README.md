# 🧠 Chat Assistant with Session Memory

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![Docker](https://img.shields.io/badge/Container-Docker-blue)
![OpenAI](https://img.shields.io/badge/LLM-OpenAI-green)

> A personalized AI assistant that remembers your preferences, clarifies ambiguities, and maintains context across sessions.

## Table of Contents
*   [Introduction](#introduction)
*   [Key Features](#key-features)
*   [Live Demo](#live-demo)
*   [System Architecture](#system-architecture)
*   [Installation & Setup](#installation--setup)
    *   [Prerequisites](#prerequisites)
    *   [Configuration](#configuration)
    *   [Installation Options](#installation-options)
*   [Usage & Testing](#usage--testing)
*   [Technical Decisions](#technical-decisions)
*   [Project Structure](#project-structure)
*   [Future Improvements](#future-improvements)

---

## Introduction

In the era of Large Language Models (LLMs), a significant limitation persists: **"The Goldfish Memory" problem**. Standard LLM interactions are stateless; once a conversation window closes, the model forgets everything about the user. This prevents the creation of truly personalized, long-term AI companions.

**Chat Assistant with Session Memory** is an engineered solution designed to bridge this gap. It is not just a chatbot wrapper, but a **state-aware system** that introduces a persistent memory layer and intelligent query processing pipelines.

Unlike generic chatbots, this system is built to:
1.  **Remember:** It actively extracts and consolidates key facts (e.g., *"User is a DevOps Engineer"*, *"User prefers Python over Java"*) into a persistent storage, making future interactions more personalized.
2.  **Understand:** It implements **Contextual Query Rewriting**, allowing it to understand implicit references like *"fix it"* or *"rewrite that"* based on previous dialogue history.
3.  **Clarify:** It detects **Ambiguity** (Polysemy). Instead of guessing when a user asks to *"Open a bank"* (Financial vs. River), it proactively asks clarifying questions to ensure accuracy.

This project serves as a comprehensive demonstration of building **Context-Aware AI Applications** using **Python**, **Streamlit**, and **OpenAI**, fully containerized with **Docker** for production-grade reproducibility.


## Key Features

### 1. 💾 Long-Term Persistent Memory
Unlike standard sessions that reset on refresh, this assistant builds a **dynamic user profile** that evolves over time.
* **Automatic Consolidation:** A background process monitors conversation density (token usage). When the buffer is full, it triggers an LLM-based summarization engine.
* **Entity Extraction:** It identifies and extracts key facts (e.g., *Job Title, Tech Stack, Hobbies*) and Constraints (e.g., *"No Java code", "Concise answers only"*).
* **Storage:** Data is serialized into `session_memory.json`, allowing the "brain" to survive server restarts or container destruction (when volumes are mapped).

### 2. 🤔 Proactive Ambiguity Resolution
The system refuses to guess when the user's intent is unclear. It implements a **Human-in-the-loop** clarification flow.
* **Polysemy Detection:** Analyzes queries for words with multiple meanings (e.g., *"Bank"* could mean *Financial Institution* or *River Bank*).
* **Interactive Clarification:** Instead of hallucinating an answer, the UI presents distinct options (Pills) for the user to select the correct context.
* **Fallback Handling:** Safely handles edge cases where the user ignores options and changes the topic entirely.

### 3. 🔄 Contextual Query Rewriting
Enables natural, human-like conversation by resolving linguistic references.
* **Anaphora Resolution:** Understands pronouns like *"it", "that", "him"* by looking back at conversation history.
* **Query Expansion:** Automatically rewrites short queries into fully self-contained prompts before sending them to the LLM.
    * *User:* "Why is it slow?" (Context: Python)
    * *System Rewrites:* "Why is **Python** slow?"

### 4. 🛡️ Robust Engineering & Architecture
Built with a focus on stability and reproducibility.
* **Structured Outputs:** Leverages **Pydantic** models to enforce strict JSON schemas for all LLM outputs, eliminating parsing errors.
* **Dockerized Deployment:** Includes a dual-mode Docker setup (Web UI + CLI), ensuring the application runs identically on any machine.
* **Safe State Management:** Handles Streamlit's rerun cycles gracefully to prevent infinite loops or state loss.


## System Architecture


## Live Demo

## Installation & Setup

### Prerequisites
* **Docker & Docker Compose** (Recommended)
* Or Python 3.12+ (For local execution)
* OpenAI API Key

### Configuration
1.  Clone the repository.
    ```bash
    git clone https://github.com/gitHuyNgo/chat-assistant-session-memory.git
    cd chat-assistant-session-memory
    ```
2.  Create your environment file:
    ```bash
    cp .env.example .env
    ```
3.  Add your API Key to `.env`:
    ```ini
    OPENAI_API_KEY=sk-proj-xxxxxxxx...
    ```
### Installation Options
You can choose one of the following methods to install the dependencies:
#### Option A: Docker
This is the **recommended** method as it handles all system dependencies automatically.
```bash
# Build the image and start the container
docker-compose up --build -d
```
#### Option B: Local Python Setup
```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Usage & Testing
Once the application is up and running, you can interact with it via the Web UI or the CLI.
### 🖥️ Mode 1: Interactive Web UI
If you followed the installation steps, the web interface is accessible at:
👉 **[http://localhost:8501](http://localhost:8501)**

#### Demo Walkthrough
To verify the core requirements quickly, use the **Test Scenarios** panel in the sidebar:

**1. Ambiguity Handling (Flow 2)**
* **Action:** Click the `Ambiguity` button.
* **Scenario:** Loads the query *"I want to open a bank"*.
* **Outcome:** The system detects the polysemy (Financial vs. River) and presents clickable **Clarification Pills** instead of guessing.

**2. Context Awareness**
* **Action:** Click the `Context` button.
* **Scenario:** Loads a history where the user dislikes Java and loves Python.
* **Outcome:** When you ask *"Write code for it"*, the system automatically generates **Python** code, proving it understands the implicit context.

**3. Memory Consolidation (Flow 1)**
* **Action:** Click the `Memory` button.
* **Scenario:** Simulates a long conversation to fill the token buffer.
* **Outcome:**
    1.  The **Buffer Usage** bar hits 100%.
    2.  A background summarization process is triggered.
    3.  The **Consolidated Memory** expander updates with new facts (e.g., *Job: DevOps, Interest: AI*).
    4.  A `session_memory.json` file is persisted in the `data/` directory.

---
### ⌨️ Mode 2: CLI Validation

You can execute the evaluation flows directly from the command line. This is useful for CI/CD pipelines or headless testing.

**Note:** If running with Docker, use `docker-compose run` to execute commands inside the isolated container.

#### Test Flow 1: Memory & Summarization
Run a simulation of a long user session to test the memory manager.
```bash
docker-compose run --rm ai-assistant python app/cli.py run-log tests/data/long_session.json
```

#### Test Flow 2: Ambiguity Detection
Run the specific ambiguity test case.
```bash
docker-compose run --rm ai-assistant python app/cli.py run-log tests/data/ambiguous.json
```

#### Test Flow 3: Instant extraction
Run the specific instant extraction test case.
```bash
docker-compose run --rm ai-assistant python app/cli.py run-log tests/data/context.json
```

## Technical Decisions


## Project Structure
```plaintext
.
├── app/
│   ├── ui.py              # Main Streamlit Application (Frontend)
│   └── cli.py             # CLI Entry point (Testing/CI)
├── src/
│   ├── core/              # Core Logic (Memory Manager, Pipeline, Generator)
│   ├── schemas/           # Pydantic Models (Data Validation)
│   └── utils/             # Helpers (Tokenizer, Storage)
├── tests/data/            # JSON Simulation logs (Test Cases)
├── data/                  # Persistent Storage (Generated at runtime)
├── Dockerfile             # Container Definition
└── docker-compose.yml     # Orchestration
```

## Future Improvements