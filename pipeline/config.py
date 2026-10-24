"""Settings shared by the pipeline, the API and the static export."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("TRACKER_DB", ROOT / "data" / "tracker.db"))
SNAPSHOT_PATH = ROOT / "dashboard" / "public" / "data" / "snapshot.json"

USER_AGENT = "trend-sentiment-tracker/1.0 (+https://github.com/EthanYap123/trend-sentiment-tracker)"
HTTP_TIMEOUT = 20

# How far back the pipeline keeps articles. The static snapshot carries all of
# them, so the Pages demo and the API answer every query the same way.
RETENTION_DAYS = 90

# Hacker News stories below this score are mostly noise for trend tracking.
HN_MIN_POINTS = 20

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "CNBC Tech": "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    "Wired": "https://www.wired.com/feed/rss",
    "Engadget": "https://www.engadget.com/rss.xml",
}

# Sector dictionaries. An article goes to the sector with the most keyword hits
# (ties go to the sector listed first), or to "General Tech" when nothing matches.
SECTORS = {
    "AI & ML": [
        "ai", "artificial intelligence", "llm", "llms", "machine learning", "neural",
        "gpt", "chatgpt", "openai", "gemini", "deepmind", "copilot",
        "agentic", "ai agent", "ai agents", "transformer", "generative", "chatbot", "chatbots",
        "inference", "model", "models",
    ],
    "Cloud & DevOps": [
        "cloud", "aws", "azure", "gcp", "google cloud", "kubernetes", "k8s", "docker", "devops",
        "serverless", "terraform", "data center", "data centers", "datacenter", "outage",
        "cloudflare", "cdn", "infrastructure",
    ],
    "Cybersecurity": [
        "security", "breach", "breached", "hack", "hacked", "hacker", "hackers", "ransomware",
        "malware", "vulnerability", "vulnerabilities", "exploit", "exploited", "cve", "phishing",
        "zero-day", "encryption", "privacy", "leak", "leaked", "spyware", "cyberattack",
    ],
    "Hardware & Chips": [
        "nvidia", "amd", "intel", "tsmc", "chip", "chips", "chipmaker", "semiconductor",
        "semiconductors", "gpu", "gpus", "cpu", "qualcomm", "processor", "smartphone", "iphone",
        "pixel", "laptop", "hardware", "headphones", "console",
    ],
    "Crypto & Fintech": [
        "crypto", "cryptocurrency", "bitcoin", "ethereum", "blockchain", "stablecoin",
        "stablecoins", "fintech", "payments", "stripe", "coinbase", "defi", "web3", "nft",
        "banking", "bank",
    ],
    "Software & Dev": [
        "programming", "programmer", "developer", "developers", "javascript", "typescript",
        "python", "rust", "golang", "java", "open source", "open-source", "github", "framework",
        "react", "linux", "compiler", "database", "postgres", "sqlite", "api", "frontend",
        "backend", "code", "coding", "software",
    ],
    "Markets & Business": [
        "stock", "stocks", "shares", "earnings", "revenue", "ipo", "valuation", "funding",
        "raises", "raised", "acquisition", "acquires", "merger", "investors", "investor",
        "nasdaq", "profit", "antitrust", "regulators", "tariff", "tariffs", "startup", "startups",
        "billion", "market",
    ],
    "Jobs & Careers": [
        "hiring", "jobs", "job", "career", "careers", "layoffs", "laid off", "job cuts",
        "remote work", "interview", "interviews", "salary", "salaries", "recruiting",
        "workforce", "internship", "employees", "workers",
    ],
    "Science & Energy": [
        "science", "scientists", "research", "researchers", "study", "physics", "quantum",
        "space", "spacex", "nasa", "rocket", "satellite", "mars", "moon", "telescope", "climate",
        "energy", "solar", "nuclear", "battery", "batteries", "fusion", "ev", "evs",
        "electric vehicle", "electric vehicles", "biology", "medical", "health", "brain",
    ],
    "Policy & Law": [
        "law", "laws", "lawsuit", "court", "judge", "ruling", "government", "congress", "senate",
        "eu", "ftc", "doj", "regulation", "regulators", "ban", "banned", "bill", "police",
        "surveillance", "censorship", "copyright", "patent", "election", "trump", "supreme court",
    ],
}
DEFAULT_SECTOR = "General Tech"
SECTOR_NAMES = [*SECTORS, DEFAULT_SECTOR]

# Trend terms tracked over time: display name -> phrases that count as a mention.
TRACKED_TERMS = {
    "AI agents": ["ai agent", "ai agents", "agentic"],
    "LLMs": ["llm", "llms", "large language model", "large language models"],
    "OpenAI": ["openai", "chatgpt"],
    "Gemini": ["gemini"],
    "Nvidia": ["nvidia"],
    "Apple": ["apple", "iphone", "ipad", "macos", "ios"],
    "Google": ["google", "alphabet", "android"],
    "Microsoft": ["microsoft", "windows"],
    "Meta": ["meta", "facebook", "instagram", "whatsapp"],
    "Amazon": ["amazon", "aws"],
    "Tesla": ["tesla"],
    "Rust": ["rust"],
    "Python": ["python"],
    "JavaScript": ["javascript", "typescript", "node.js"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Linux": ["linux"],
    "Open source": ["open source", "open-source"],
    "Bitcoin": ["bitcoin", "btc"],
    "Crypto": ["crypto", "cryptocurrency", "stablecoin", "stablecoins"],
    "Layoffs": ["layoffs", "laid off", "job cuts"],
    "Hiring": ["hiring", "recruiting"],
    "Funding rounds": ["funding", "raises", "series a", "series b", "seed round"],
    "IPOs": ["ipo", "ipos"],
    "Antitrust": ["antitrust", "monopoly"],
    "Ransomware": ["ransomware"],
    "Data breaches": ["breach", "breached", "data leak"],
    "Chips": ["chip", "chips", "semiconductor", "semiconductors", "chipmaker"],
    "Data centers": ["data center", "data centers", "datacenter", "datacenters"],
    "Quantum": ["quantum"],
    "Robotics": ["robot", "robots", "robotics", "humanoid"],
    "EVs": ["ev", "evs", "electric vehicle", "electric vehicles"],
    "Space": ["spacex", "nasa", "rocket", "satellite", "satellites"],
    "Privacy": ["privacy"],
    "Tariffs": ["tariff", "tariffs"],
    "Startups": ["startup", "startups"],
    "Energy": ["nuclear", "solar", "battery", "batteries", "power grid"],
    "Regulation": ["regulation", "regulators", "ftc", "lawsuit", "court"],
}
