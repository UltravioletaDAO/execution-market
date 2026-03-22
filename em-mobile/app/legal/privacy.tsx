import { View, Text, ScrollView, Pressable } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

export default function PrivacyPolicyScreen() {
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
        <Text className="text-white text-xl font-bold">{t("legal.privacyPolicy")}</Text>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        <View className="bg-surface rounded-2xl p-4 mt-2 mb-4">
          <Text className="text-gray-500 text-xs uppercase font-bold mb-3">
            {t("legal.lastUpdated")}: 2026-03-21
          </Text>

          <Text className="text-white text-lg font-bold mb-2">
            {t("legal.privacyPolicy")}
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Execution Market ("we," "our," or "us") is operated by Ultravioleta DAO. This Privacy Policy describes how we collect, use, disclose, and protect your personal information when you use the Execution Market mobile application, website (execution.market), and related services (collectively, the "Platform"). By using the Platform, you consent to the practices described in this policy.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            1. Information We Collect
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-1">
            We collect the following categories of information:
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} Email address -- used for account authentication via one-time passcode (OTP) through our authentication provider (Dynamic.xyz). We do not store your password.{"\n\n"}
            {"\u2022"} Display name and bio -- profile information you voluntarily provide to identify yourself to task publishers and other platform participants.{"\n\n"}
            {"\u2022"} Wallet address -- your public blockchain wallet address, used to process digital payments and record on-chain reputation. Wallet addresses are inherently public on blockchain networks.{"\n\n"}
            {"\u2022"} Precise location data -- GPS coordinates collected with your permission when you submit task evidence. Location is used to verify physical task completion (e.g., confirming you visited a required location) and to show nearby available tasks.{"\n\n"}
            {"\u2022"} Photos and camera data -- images you capture and submit as task completion evidence. Photos may include embedded metadata such as EXIF data (timestamp, GPS coordinates, device information).{"\n\n"}
            {"\u2022"} Device information -- device model, operating system version, unique device identifiers, and app version. Collected for crash diagnostics, fraud prevention, and service improvement.{"\n\n"}
            {"\u2022"} Usage data -- interaction patterns within the app, including pages viewed, tasks browsed, and feature usage. Collected to improve the Platform experience.{"\n\n"}
            {"\u2022"} Communication data -- messages sent through in-app messaging (XMTP), which are end-to-end encrypted. We cannot read message contents.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            2. How We Use Your Information
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} To authenticate your identity and manage your account.{"\n\n"}
            {"\u2022"} To facilitate task publishing, discovery, acceptance, and completion.{"\n\n"}
            {"\u2022"} To process digital payments in stablecoins (USDC, EURC, USDT, PYUSD, AUSD) via gasless transactions.{"\n\n"}
            {"\u2022"} To verify task evidence submissions, including AI-assisted and human review of photos, location data, and timestamps.{"\n\n"}
            {"\u2022"} To maintain your on-chain reputation score under the ERC-8004 identity standard.{"\n\n"}
            {"\u2022"} To detect and prevent fraud, GPS spoofing, duplicate accounts, and other abusive behavior.{"\n\n"}
            {"\u2022"} To communicate with you about task updates, platform announcements, and support inquiries.{"\n\n"}
            {"\u2022"} To improve the Platform, diagnose technical issues, and develop new features.{"\n\n"}
            {"\u2022"} To comply with applicable legal obligations.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            3. Location Data
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We collect precise GPS location data only when you explicitly grant permission through your device settings. Location data is used for two purposes: (a) verifying that physical tasks were completed at the required location, and (b) showing you tasks available near your current position. You may revoke location permissions at any time through your device settings. Revoking location access may limit your ability to submit evidence for location-dependent tasks.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            4. Camera and Photo Data
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Camera access is requested only when you choose to capture evidence for a task submission. Photos you submit are uploaded to our secure storage infrastructure (Amazon Web Services S3) and delivered through a content delivery network (AWS CloudFront). Submitted photos are retained as long as the associated task record exists and may be used for dispute resolution. Photos may be reviewed by automated AI verification systems and, when necessary, by human moderators.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            5. Blockchain Data and Permanence
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Certain data is recorded on public blockchain networks (including but not limited to Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, and Monad) and becomes permanent and publicly accessible. This includes:{"\n\n"}
            {"\u2022"} Payment transactions (amounts, sender and recipient wallet addresses, timestamps).{"\n\n"}
            {"\u2022"} Reputation scores and feedback records under the ERC-8004 identity standard.{"\n\n"}
            {"\u2022"} Agent and worker identity registration records.{"\n\n"}
            By using the Platform, you acknowledge and accept that blockchain data is immutable. We cannot modify, delete, or restrict access to information recorded on public blockchains, even upon your request or account deletion. This is an inherent characteristic of blockchain technology, not a policy choice.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            6. Third-Party Service Providers
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-1">
            We share information with the following third-party service providers, each of which processes data in accordance with their own privacy policies:
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} Dynamic.xyz -- authentication provider. Receives your email address to generate OTP login codes and manage wallet connections.{"\n\n"}
            {"\u2022"} Supabase -- database infrastructure (PostgreSQL). Stores account profiles, task records, submissions, and application data. Hosted in the United States.{"\n\n"}
            {"\u2022"} Amazon Web Services (AWS) -- cloud infrastructure. Evidence files (photos) are stored in AWS S3 and served through CloudFront CDN. Compute services run on AWS ECS. Hosted in the United States (us-east-2 region).{"\n\n"}
            {"\u2022"} XMTP -- decentralized messaging protocol. Facilitates end-to-end encrypted communications between platform participants. We do not have access to message contents.{"\n\n"}
            {"\u2022"} Sentry -- error monitoring and crash reporting. Receives anonymized device and error data to help us diagnose and fix application issues.{"\n\n"}
            We do not sell your personal information to third parties. We do not share your information with third parties for their own marketing purposes.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            7. Data Storage and Security
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We implement industry-standard technical and organizational measures to protect your information, including encryption in transit (TLS/HTTPS), database row-level security policies, secure access controls, and encrypted storage of sensitive credentials. While we strive to protect your data, no method of electronic transmission or storage is completely secure, and we cannot guarantee absolute security.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            8. Data Retention
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We retain your off-chain personal data for as long as your account is active or as needed to provide services. Upon account deletion, we will delete or anonymize your off-chain data within 30 days, except where retention is required by law or for legitimate business purposes (such as fraud prevention or dispute resolution of completed tasks). On-chain data is retained permanently as described in Section 5.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            9. Account Deletion
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            You may request deletion of your account and associated off-chain data at any time by:{"\n\n"}
            {"\u2022"} Using the "Delete Account" option in the app Settings screen.{"\n\n"}
            {"\u2022"} Visiting execution.market/delete-account on the web.{"\n\n"}
            {"\u2022"} Contacting us at executionmarket@proton.me.{"\n\n"}
            Upon deletion, your profile information, email, display name, and submission records stored off-chain will be removed. On-chain data (payment transactions, reputation scores, identity records) will persist on the blockchain and cannot be deleted.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            10. Children's Privacy
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            The Platform is not intended for individuals under 18 years of age. We do not knowingly collect personal information from children under 18. If we learn that we have collected information from a child under 18, we will promptly delete that information. If you believe a child under 18 has provided us with personal data, please contact us at executionmarket@proton.me.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            11. Your Rights Under GDPR (EEA/UK Users)
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            If you are located in the European Economic Area or the United Kingdom, you have the following rights regarding your off-chain personal data:{"\n\n"}
            {"\u2022"} Right of access -- request a copy of the personal data we hold about you.{"\n\n"}
            {"\u2022"} Right to rectification -- request correction of inaccurate personal data.{"\n\n"}
            {"\u2022"} Right to erasure -- request deletion of your personal data (subject to the blockchain limitations described in Section 5).{"\n\n"}
            {"\u2022"} Right to restrict processing -- request that we limit how we use your data.{"\n\n"}
            {"\u2022"} Right to data portability -- request your data in a structured, machine-readable format.{"\n\n"}
            {"\u2022"} Right to object -- object to processing based on legitimate interests.{"\n\n"}
            To exercise these rights, contact us at executionmarket@proton.me. We will respond within 30 days. Note that these rights apply only to off-chain data. On-chain blockchain data is technically immutable and cannot be modified or erased by any party.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            12. Your Rights Under CCPA (California Residents)
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            If you are a California resident, you have the right to:{"\n\n"}
            {"\u2022"} Know what personal information we collect, use, and disclose.{"\n\n"}
            {"\u2022"} Request deletion of your personal information (subject to blockchain limitations).{"\n\n"}
            {"\u2022"} Opt out of the sale of personal information. We do not sell your personal information.{"\n\n"}
            {"\u2022"} Non-discrimination for exercising your privacy rights.{"\n\n"}
            To exercise these rights, contact us at executionmarket@proton.me.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            13. Cookies and Tracking
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            The Execution Market mobile application does not use cookies. We do not use advertising trackers or cross-app tracking. Minimal analytics data may be collected for service improvement and crash diagnostics. The web version of the Platform (execution.market) may use essential cookies for session management.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            14. International Data Transfers
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Your information may be transferred to and processed in the United States and other countries where our service providers operate. By using the Platform, you consent to the transfer of your data to countries that may have different data protection laws than your jurisdiction. We take steps to ensure your data is treated securely and in accordance with this Privacy Policy regardless of where it is processed.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            15. Changes to This Policy
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We may update this Privacy Policy from time to time. We will notify you of material changes by posting the updated policy within the app and updating the "Last Updated" date above. Your continued use of the Platform after changes are posted constitutes acceptance of the revised policy. We encourage you to review this policy periodically.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            16. Contact Us
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            If you have any questions, concerns, or requests regarding this Privacy Policy or our data practices, please contact us at:{"\n\n"}
            Ultravioleta DAO{"\n"}
            Email: executionmarket@proton.me{"\n\n"}
            Effective Date: March 21, 2026
          </Text>
        </View>

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
