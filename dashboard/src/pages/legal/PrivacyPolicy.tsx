import { useEffect } from 'react';

export function PrivacyPolicy() {
  useEffect(() => { window.scrollTo(0, 0); }, []);

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
      <p className="text-gray-400 text-sm mb-8">Last updated: March 21, 2026</p>

      <div className="prose prose-invert prose-sm max-w-none space-y-6 text-gray-300 leading-relaxed">
        <p>
          Execution Market ("we," "our," or "us") is operated by Ultravioleta DAO. This Privacy Policy describes how we collect, use, disclose, and protect your personal information when you use the Execution Market mobile application, website (execution.market), and related services (collectively, the "Platform").
        </p>

        <h2 className="text-xl font-semibold text-white">1. Information We Collect</h2>
        <ul className="list-disc pl-5 space-y-2">
          <li><strong>Email address</strong> — used for account authentication via one-time passcode (OTP) through Dynamic.xyz.</li>
          <li><strong>Display name and bio</strong> — profile information you voluntarily provide.</li>
          <li><strong>Wallet address</strong> — your public blockchain wallet address, used to process digital payments and record reputation. Wallet addresses are inherently public on blockchain networks.</li>
          <li><strong>Precise location data</strong> — GPS coordinates collected with your permission when you submit task evidence or browse nearby tasks.</li>
          <li><strong>Photos and camera data</strong> — images you capture and submit as task completion evidence, including embedded EXIF metadata.</li>
          <li><strong>Device information</strong> — device model, OS version, and app version for crash diagnostics and fraud prevention.</li>
          <li><strong>Usage data</strong> — interaction patterns within the app to improve the Platform experience.</li>
          <li><strong>Communication data</strong> — messages sent through XMTP, which are end-to-end encrypted. We cannot read message contents.</li>
        </ul>

        <h2 className="text-xl font-semibold text-white">2. How We Use Your Information</h2>
        <ul className="list-disc pl-5 space-y-2">
          <li>To authenticate your identity and manage your account.</li>
          <li>To facilitate task publishing, discovery, acceptance, and completion.</li>
          <li>To process digital payments in stablecoins via gasless transactions.</li>
          <li>To verify task evidence submissions, including AI-assisted review.</li>
          <li>To maintain your on-chain reputation score (ERC-8004).</li>
          <li>To detect and prevent fraud, GPS spoofing, and abusive behavior.</li>
          <li>To improve the Platform and develop new features.</li>
          <li>To comply with applicable legal obligations.</li>
        </ul>

        <h2 className="text-xl font-semibold text-white">3. Location Data</h2>
        <p>
          We collect precise GPS location data only when you explicitly grant permission. Location is used to verify physical task completion and to show nearby tasks. You may revoke location permissions at any time through your device settings.
        </p>

        <h2 className="text-xl font-semibold text-white">4. Camera and Photo Data</h2>
        <p>
          Camera access is requested only when you capture evidence for a task. Photos are uploaded to secure storage (Amazon Web Services S3) and delivered through CloudFront CDN. Photos may be reviewed by automated AI systems and human moderators.
        </p>

        <h2 className="text-xl font-semibold text-white">5. Blockchain Data and Permanence</h2>
        <p>
          Certain data is recorded on public blockchain networks and becomes permanent and publicly accessible. This includes payment transactions, reputation scores, and identity records. We cannot modify, delete, or restrict access to information recorded on public blockchains. This is an inherent characteristic of blockchain technology.
        </p>

        <h2 className="text-xl font-semibold text-white">6. Third-Party Service Providers</h2>
        <ul className="list-disc pl-5 space-y-2">
          <li><strong>Dynamic.xyz</strong> — authentication. Receives your email for OTP login.</li>
          <li><strong>Supabase</strong> — database infrastructure. Stores account profiles and application data.</li>
          <li><strong>Amazon Web Services</strong> — cloud infrastructure and evidence storage.</li>
          <li><strong>XMTP</strong> — decentralized, end-to-end encrypted messaging.</li>
          <li><strong>Sentry</strong> — crash reporting and error monitoring.</li>
        </ul>
        <p>We do not sell your personal information to third parties.</p>

        <h2 className="text-xl font-semibold text-white">7. Data Retention and Deletion</h2>
        <p>
          We retain your off-chain data for as long as your account is active. Upon account deletion, off-chain data is removed within 30 days. On-chain data persists permanently.
        </p>

        <h2 className="text-xl font-semibold text-white">8. Account Deletion</h2>
        <p>You may delete your account at any time by:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Using the "Delete Account" option in the app Settings screen.</li>
          <li>Visiting <a href="/delete-account" className="text-violet-400 underline">execution.market/delete-account</a>.</li>
          <li>Emailing <a href="mailto:executionmarket@proton.me" className="text-violet-400 underline">executionmarket@proton.me</a>.</li>
        </ul>

        <h2 className="text-xl font-semibold text-white">9. Children's Privacy</h2>
        <p>The Platform is not intended for individuals under 18. We do not knowingly collect information from children under 18.</p>

        <h2 className="text-xl font-semibold text-white">10. Your Rights (GDPR / CCPA)</h2>
        <p>
          You have the right to access, correct, delete, and port your off-chain personal data. To exercise these rights, contact <a href="mailto:executionmarket@proton.me" className="text-violet-400 underline">executionmarket@proton.me</a>. We will respond within 30 days. On-chain data cannot be modified due to the immutable nature of blockchain.
        </p>

        <h2 className="text-xl font-semibold text-white">11. Contact Us</h2>
        <p>
          Ultravioleta DAO<br />
          Email: <a href="mailto:executionmarket@proton.me" className="text-violet-400 underline">executionmarket@proton.me</a>
        </p>
      </div>
    </div>
  );
}
