# back/Services/rules_refresh.py
import logging
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "policy-ingestion-mvp"))

import policy_parser_ai as policy_parser

def refresh_rules_job():
    logging.info("🔄 Refreshing rules from YouTube...")
    try:
        urls = policy_parser.get_catalog()
        for entry in urls:
            policy_parser.to_rule_doc(entry["loc"])
        logging.info("✅ Rules updated successfully")
        return {"status": "ok", "message": "Rules updated"}
    except Exception as e:
        logging.error(f"❌ Rule refresh failed: {e}")
        return {"status": "error", "message": str(e)}
