# VisionWealth Portfolio Analytics Platform

VisionWealth is a comprehensive, AI-powered portfolio analytics dashboard designed for high-net-worth individuals and wealth managers. It provides deep insights, real-time benchmarking, and goal tracking to optimize investment strategies.

## 🚀 Features

### 📊 Advanced Analytics
- **Portfolio Overview**: Real-time valuation, daily change, and asset allocation.
- **Deep Dive**: Sector breakdown, risk metrics (Beta, Sharpe Ratio), and yield analysis.
- **Interactive Charts**: Dynamic visualization of performance and allocation.

### 🧠 AI Insights (Powered by OpenAI)
- **Smart Analysis**: Automated executive summaries of your portfolio's health.
- **Risk & Opportunity Detection**: AI-driven identification of concentration risks and income opportunities.
- **Market Sentiment**: Real-time sentiment analysis based on your holdings.

### 📈 Benchmarking
- **S&P 500 Comparison**: Track your portfolio's performance against the market index (SPY).
- **Historical Data**: 1-year performance comparison using real-time market data.

### 🎯 Goal Tracking
- **Financial Goals**: Set and track progress towards major life events (Retirement, Home Purchase).
- **Progress Visualization**: Visual indicators of your journey towards each target.

### 📄 Reporting & Export
- **PDF Reports**: Generate professional, client-ready portfolio summaries.
- **CSV Export**: Download full portfolio data for external modeling.

### 🔐 Security & Architecture
- **Secure Authentication**: JWT-based login and registration system.
- **Robust Backend**: FastAPI (Python) with PostgreSQL database.
- **Modern Frontend**: Responsive HTML/JS dashboard with glassmorphism design.

## 🛠️ Tech Stack

- **Frontend**: HTML5, TailwindCSS, Vanilla JavaScript, Chart.js
- **Backend**: Python, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL (via Railway)
- **AI Engine**: OpenAI GPT-4
- **Data Sources**: Yahoo Finance (`yfinance`)

## 📦 Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL
- OpenAI API Key

### Local Development

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/visionwealth.git
    cd visionwealth
    ```

2.  **Backend Setup**
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**
    Create a `.env` file in `backend/`:
    ```env
    DATABASE_URL=postgresql://user:pass@localhost/visionwealth
    SECRET_KEY=your_secret_key
    OPENAI_API_KEY=sk-proj-...
    ```

4.  **Run the Application**
    ```bash
    # Run database migrations
    alembic upgrade head

    # Start the server
    uvicorn main:app --reload
    ```

5.  **Access the Dashboard**
    Open `frontend/index.html` in your browser (or serve via a simple HTTP server).

## 🚀 Deployment

This project is optimized for deployment on **Railway** (Backend + DB) and **Vercel** (Frontend).

See [DEPLOYMENT_GUIDE.md](deployment_guide.md) for detailed instructions.

## 📄 License

MIT License - see LICENSE for details.
