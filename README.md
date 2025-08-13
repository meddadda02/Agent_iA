# Agent_iA
install  
npm install --legacy-peer-deps
apres 
npm run dev



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

