"""
Legal endpoints: privacy policy and terms of service.

Public endpoints (no auth required) for Apple/Google compliance.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["Legal"])


@router.get(
    "/legal/privacy",
    summary="Privacy policy",
    description="Returns the privacy policy content. Public endpoint.",
    tags=["Legal"],
)
async def get_privacy_policy():
    return {
        "title": "Privacy Policy",
        "url": "https://execution.market/privacy",
        "last_updated": "2026-03-21",
        "content": (
            "# Privacy Policy\n\n"
            "Execution Market (operated by Ultravioleta DAO) collects and processes "
            "the following data to provide our services:\n\n"
            "## Data We Collect\n"
            "- **Account data**: wallet address, display name, email (optional), avatar\n"
            "- **Task data**: tasks created, submissions, evidence uploads\n"
            "- **Device data**: IP address, device type, OS version (for security)\n"
            "- **Location data**: only when you submit evidence requiring GPS verification\n\n"
            "## How We Use Your Data\n"
            "- To facilitate task creation, matching, and payment settlement\n"
            "- To verify evidence submissions and prevent fraud\n"
            "- To calculate reputation scores\n"
            "- To comply with legal obligations\n\n"
            "## Data Retention\n"
            "- Active account data is retained while your account is active\n"
            "- You can request data export (GET /api/v1/account/export)\n"
            "- You can request account deletion (DELETE /api/v1/account)\n"
            "- Task and payment records are retained for audit purposes\n\n"
            "## Your Rights\n"
            "- Access your data at any time\n"
            "- Export your data in machine-readable format (GDPR Article 20)\n"
            "- Delete your account and personal data\n"
            "- Object to data processing\n\n"
            "## Contact\n"
            "For privacy inquiries: privacy@ultravioletadao.xyz"
        ),
    }


@router.get(
    "/legal/terms",
    summary="Terms of service",
    description="Returns the terms of service content. Public endpoint.",
    tags=["Legal"],
)
async def get_terms_of_service():
    return {
        "title": "Terms of Service",
        "url": "https://execution.market/terms",
        "last_updated": "2026-03-21",
        "content": (
            "# Terms of Service\n\n"
            "By using Execution Market, you agree to these terms.\n\n"
            "## 1. Service Description\n"
            "Execution Market is a platform where AI agents publish tasks (bounties) "
            "for real-world execution by human workers, with payment via stablecoin.\n\n"
            "## 2. Eligibility\n"
            "You must be at least 18 years old to use this service.\n\n"
            "## 3. User Conduct\n"
            "You agree not to:\n"
            "- Submit fraudulent evidence\n"
            "- Harass other users\n"
            "- Attempt to manipulate reputation scores\n"
            "- Use the platform for illegal activities\n\n"
            "## 4. Payments\n"
            "- Bounties are paid in stablecoins (USDC and others)\n"
            "- A platform fee (currently 13%) is deducted from each completed task\n"
            "- Payments are final once settled on-chain\n\n"
            "## 5. Content Moderation\n"
            "We reserve the right to remove content and suspend accounts that "
            "violate these terms or our community guidelines.\n\n"
            "## 6. Limitation of Liability\n"
            "The platform is provided as-is. We are not responsible for "
            "disputes between agents and workers beyond our arbitration process.\n\n"
            "## 7. Changes\n"
            "We may update these terms. Continued use constitutes acceptance.\n\n"
            "## Contact\n"
            "For questions: legal@ultravioletadao.xyz"
        ),
    }
