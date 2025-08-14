# Agent_iA
install  
npm install --legacy-peer-deps
apres 
npm run dev

# create admin
cd back
python create_admin.py
# flux rss
-------------------for  policies
cd policy-ingestion-mvp
pip install httpx selectolax
pip install apscheduler 
pip install spacy yake nltk
python -m spacy download en_core_web_sm*
pip install beautifulsoup4 
python sitemap_crawler.py
python policy_parser_ai.py



in the database run
ALTER TABLE rules
ADD COLUMN scope TEXT[] DEFAULT '{}',
ADD COLUMN prohibits TEXT[] DEFAULT '{}',
ADD COLUMN allows_if TEXT[] DEFAULT '{}',
ADD COLUMN examples_positive TEXT[] DEFAULT '{}',
ADD COLUMN examples_negative TEXT[] DEFAULT '{}',
ADD COLUMN keywords TEXT;

option2
CREATE TABLE rules (
    id SERIAL PRIMARY KEY,
    title TEXT,
    link TEXT,
    content TEXT,
    published_at TIMESTAMP,
    source TEXT,
    hash TEXT UNIQUE,
    scope TEXT[] DEFAULT '{}',
    prohibits TEXT[] DEFAULT '{}',
    allows_if TEXT[] DEFAULT '{}',
    examples_positive TEXT[] DEFAULT '{}',
    examples_negative TEXT[] DEFAULT '{}',
    keywords TEXT
);