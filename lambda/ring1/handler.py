"""Ring 1 PHOTINT Verification Lambda Handler (stub).

Receives SQS messages containing submission IDs and evidence metadata.
In Phase 2, this will run the full PHOTINT pipeline:
  - Download evidence images from S3
  - EXIF extraction (GPS, timestamps, device info)
  - Perceptual hashing (duplicate/manipulation detection)
  - AI semantic verification (Gemini/Anthropic/OpenAI)
  - Update submission status in Supabase
  - Optionally enqueue Ring 2 arbiter evaluation

For now, this is a stub that logs the received message and returns success.
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    """Process Ring 1 verification messages from SQS."""
    records = event.get("Records", [])
    logger.info("Ring 1 stub: received %d record(s)", len(records))

    for record in records:
        body = json.loads(record["body"])
        submission_id = body.get("submission_id", "unknown")
        task_id = body.get("task_id", "unknown")
        logger.info(
            "Ring 1 stub: submission=%s task=%s — would run PHOTINT pipeline",
            submission_id,
            task_id,
        )

    return {"statusCode": 200, "body": json.dumps({"processed": len(records)})}
