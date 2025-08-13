from apscheduler.schedulers.blocking import BlockingScheduler
import policy_parser

scheduler = BlockingScheduler()

@scheduler.scheduled_job('interval', hours=24)
def update_rules():
    print("🔄 Checking for policy updates...")
    print(f"Checking: {entry['loc']}")

    urls = policy_parser.get_catalog()
    for entry in urls:
        policy_parser.to_rule_doc(entry["loc"])
    print("✅ Rules updated.")


scheduler.start()
