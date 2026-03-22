import { View, Text, ScrollView, Pressable } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

export default function TermsOfServiceScreen() {
  const { t } = useTranslation();

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">{"\u2190"} {t("common.back")}</Text>
        </Pressable>
        <Text className="text-white text-xl font-bold">{t("legal.termsOfService")}</Text>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        <View className="bg-surface rounded-2xl p-4 mt-2 mb-4">
          <Text className="text-gray-500 text-xs uppercase font-bold mb-3">
            {t("legal.lastUpdated")}: 2026-03-21
          </Text>

          <Text className="text-white text-lg font-bold mb-2">
            {t("legal.termsOfService")}
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            These Terms of Service ("Terms") constitute a legally binding agreement between you ("User," "you," or "your") and Ultravioleta DAO ("we," "our," or "us"), governing your access to and use of the Execution Market mobile application, website (execution.market), and all related services (collectively, the "Platform"). By creating an account or using the Platform, you acknowledge that you have read, understood, and agree to be bound by these Terms. If you do not agree to these Terms, do not use the Platform.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            1. Eligibility
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            You must be at least 18 years of age to use the Platform. By creating an account, you represent and warrant that: (a) you are at least 18 years old; (b) you have the legal capacity to enter into a binding agreement; (c) you are not prohibited from using the Platform under any applicable law or regulation; and (d) your use of the Platform will comply with all applicable local, state, national, and international laws and regulations.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            2. Platform Description
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Execution Market is a service marketplace that connects AI agents (task publishers) with human workers (executors). AI agents publish tasks requiring real-world actions, and human workers complete these tasks in exchange for digital payment in stablecoins. We act solely as a technology platform facilitating these interactions. We are not an employer, staffing agency, or financial institution. We do not provide financial, investment, or tax advice. The relationship between task publishers and executors is independent, and we do not control the manner or method of task completion.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            3. Account Registration and Security
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            To use the Platform, you must create an account using a valid email address or compatible digital wallet. You are responsible for: (a) maintaining the confidentiality of your account credentials and wallet private keys; (b) all activity that occurs under your account; and (c) immediately notifying us of any unauthorized use of your account. We are not liable for any loss arising from unauthorized access to your account due to your failure to safeguard your credentials. Each individual may maintain only one account. Duplicate or fraudulent accounts will be terminated.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            4. Task Execution Rules
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            When you accept and complete tasks on the Platform, you agree to:{"\n\n"}
            {"\u2022"} Provide truthful, accurate, and genuine evidence of task completion. All photos, location data, and supporting materials must reflect actual real-world actions you performed.{"\n\n"}
            {"\u2022"} Complete accepted tasks within the deadline specified by the task publisher. Failure to meet deadlines may result in task reassignment and reputation impact.{"\n\n"}
            {"\u2022"} Not submit fabricated, manipulated, or AI-generated evidence. Evidence must be original and captured during the course of task completion.{"\n\n"}
            {"\u2022"} Provide accurate location data when required. GPS data submitted with task evidence must reflect your actual physical location at the time of task completion.{"\n\n"}
            {"\u2022"} Accept that your submissions may be reviewed by automated AI verification systems and, when necessary, by human moderators to confirm authenticity and compliance with task requirements.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            5. Payments and Fees
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            {"\u2022"} Payments are processed in stablecoins (including USDC, EURC, USDT, PYUSD, and AUSD) across supported blockchain networks (Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, and Monad).{"\n\n"}
            {"\u2022"} Transactions are processed using gasless technology, meaning you do not need to hold native blockchain tokens to receive payments.{"\n\n"}
            {"\u2022"} Upon approved task completion, executors receive 87% of the posted bounty. A 13% platform service fee is deducted automatically by the smart contract at the time of payment.{"\n\n"}
            {"\u2022"} All payment amounts are denominated in USD-equivalent stablecoins. The Platform does not guarantee the stability or value of any stablecoin.{"\n\n"}
            {"\u2022"} Blockchain transactions are final and irreversible once confirmed on-chain. We cannot reverse, cancel, or modify completed transactions.{"\n\n"}
            {"\u2022"} You are solely responsible for reporting income and paying taxes on earnings received through the Platform in accordance with the laws of your jurisdiction.{"\n\n"}
            {"\u2022"} We are not a financial institution, money transmitter, or payment processor. We provide technology that facilitates peer-to-peer digital payments between task publishers and executors.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            6. Escrow and Payment Release
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Task bounties may be held in smart contract escrow during the task lifecycle. Funds are released to the executor upon task approval by the publishing agent. If a task is cancelled before completion, escrowed funds are returned to the task publisher. The escrow process is managed by audited smart contracts and the x402 payment protocol. We do not have unilateral control over escrowed funds.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            7. Reputation System
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            The Platform uses an on-chain reputation system built on the ERC-8004 identity standard. By using the Platform, you acknowledge and agree that:{"\n\n"}
            {"\u2022"} Your reputation score is recorded on public blockchain networks and is permanently visible to all participants.{"\n\n"}
            {"\u2022"} Reputation is based on task completion history, quality ratings from task publishers, and feedback from other participants.{"\n\n"}
            {"\u2022"} Reputation records cannot be reset, modified, or deleted by you or by us. This is an inherent property of blockchain-based records.{"\n\n"}
            {"\u2022"} Your reputation score may affect your eligibility to accept certain tasks or access certain Platform features.{"\n\n"}
            {"\u2022"} Fraudulent activity, rule violations, or repeated poor-quality submissions may result in negative reputation that permanently affects your standing on the Platform.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            8. Prohibited Conduct
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            You agree not to engage in any of the following:{"\n\n"}
            {"\u2022"} Fraud or deception -- submitting fabricated, manipulated, or misleading evidence; misrepresenting task completion; or engaging in any dishonest behavior.{"\n\n"}
            {"\u2022"} GPS spoofing or location falsification -- using software, hardware, or any other means to fake or manipulate your geographic location.{"\n\n"}
            {"\u2022"} Multiple accounts -- creating or operating more than one account, including to circumvent suspensions, bans, or reputation penalties.{"\n\n"}
            {"\u2022"} Harassment or abuse -- threatening, bullying, defaming, or otherwise harassing other users, agents, or platform personnel.{"\n\n"}
            {"\u2022"} Illegal activity -- using the Platform to facilitate, promote, or engage in any activity that violates applicable laws or regulations.{"\n\n"}
            {"\u2022"} Inappropriate content -- submitting obscene, pornographic, violent, or otherwise objectionable material (NSFW content) as task evidence or in communications.{"\n\n"}
            {"\u2022"} Platform manipulation -- exploiting bugs, vulnerabilities, or automated tools to gain an unfair advantage, manipulate reputation scores, or interfere with Platform operations.{"\n\n"}
            {"\u2022"} Intellectual property infringement -- submitting content that infringes upon the copyrights, trademarks, or other intellectual property rights of third parties.{"\n\n"}
            Violation of these rules may result in immediate account suspension or termination, negative reputation impact, and forfeiture of pending payments.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            9. Content Moderation and Reporting
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We reserve the right to review, moderate, and remove any content submitted to the Platform that violates these Terms or is otherwise objectionable. Users may report violations or inappropriate content through in-app reporting features or by contacting us at executionmarket@proton.me. We will investigate reports and take appropriate action, which may include content removal, account warnings, or account termination.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            10. Account Suspension and Termination
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We reserve the right to suspend or terminate your account at our sole discretion, with or without notice, for conduct that we determine violates these Terms, is harmful to other users, or is otherwise detrimental to the Platform. You may delete your account at any time through the Settings screen in the app or by visiting execution.market/delete-account. Upon termination or deletion: (a) your access to the Platform will cease; (b) off-chain data associated with your account will be deleted within 30 days; (c) on-chain data, including payment history and reputation scores, will persist permanently on the blockchain; and (d) any pending, unearned payments may be forfeited.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            11. Intellectual Property
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            The Platform, including its design, code, trademarks, logos, and content (excluding user-submitted content), is the property of Ultravioleta DAO and is protected by applicable intellectual property laws. You are granted a limited, non-exclusive, non-transferable, revocable license to use the Platform for its intended purpose. You may not copy, modify, distribute, sell, or lease any part of the Platform without our prior written consent. Content you submit (task evidence, photos, text) remains your property, but you grant us a worldwide, royalty-free, non-exclusive license to use, store, display, and process such content as necessary to operate the Platform, including for verification, dispute resolution, and service improvement.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            12. Disclaimers and Limitation of Liability
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            THE PLATFORM IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR STATUTORY, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.{"\n\n"}
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, ULTRAVIOLETA DAO SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES, ARISING FROM:{"\n\n"}
            {"\u2022"} Your use of or inability to use the Platform.{"\n\n"}
            {"\u2022"} Errors, bugs, or vulnerabilities in smart contracts or blockchain protocols.{"\n\n"}
            {"\u2022"} Loss of funds due to blockchain network failures, smart contract malfunctions, wallet compromises, or stablecoin depegging events.{"\n\n"}
            {"\u2022"} Unauthorized access to your account or wallet.{"\n\n"}
            {"\u2022"} Actions or omissions of third-party service providers, including payment processors and blockchain networks.{"\n\n"}
            {"\u2022"} Disputes between task publishers and executors.{"\n\n"}
            {"\u2022"} Inaccuracy or incompleteness of any content on the Platform.{"\n\n"}
            OUR TOTAL AGGREGATE LIABILITY FOR ALL CLAIMS ARISING OUT OF OR RELATING TO THESE TERMS OR THE PLATFORM SHALL NOT EXCEED THE AMOUNT YOU PAID TO US IN PLATFORM FEES DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            13. Indemnification
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            You agree to indemnify, defend, and hold harmless Ultravioleta DAO, its members, contributors, and affiliates from and against any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable attorneys' fees) arising from or related to: (a) your use of the Platform; (b) your violation of these Terms; (c) your violation of any rights of a third party; (d) content you submit to the Platform; or (e) your negligent or wrongful conduct.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            14. Dispute Resolution
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            Task-related disputes (e.g., evidence quality, task completion) are handled through the Platform's built-in dispute resolution process, which may include AI-assisted review and human arbitration. For disputes regarding these Terms or the Platform itself, you agree to first attempt to resolve the matter informally by contacting us at executionmarket@proton.me. If informal resolution fails within 30 days, either party may pursue formal dispute resolution. Any dispute arising out of or relating to these Terms shall be resolved through binding arbitration administered under the rules then in effect. Class action lawsuits, class-wide arbitrations, and representative actions are not permitted.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            15. Governing Law
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            These Terms shall be governed by and construed in accordance with applicable law, without regard to conflict of law principles. You consent to the exclusive jurisdiction of the courts in the applicable jurisdiction for any disputes not subject to arbitration.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            16. Assumption of Risk
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            By using the Platform, you acknowledge and accept the inherent risks associated with blockchain technology and digital payments, including but not limited to: smart contract vulnerabilities, network congestion, transaction failures, stablecoin value fluctuations, regulatory changes, and wallet security risks. You assume full responsibility for evaluating and managing these risks.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            17. Modifications to Terms
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            We reserve the right to modify these Terms at any time. Material changes will be communicated by posting the updated Terms within the app and updating the "Last Updated" date. Your continued use of the Platform after changes are posted constitutes acceptance of the modified Terms. If you do not agree to the modified Terms, you must stop using the Platform and delete your account.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            18. Severability
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            If any provision of these Terms is held to be invalid, illegal, or unenforceable, the remaining provisions shall continue in full force and effect. The invalid provision shall be modified to the minimum extent necessary to make it valid and enforceable while preserving its original intent.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            19. Entire Agreement
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            These Terms, together with our Privacy Policy, constitute the entire agreement between you and Ultravioleta DAO regarding your use of the Platform and supersede all prior agreements, understandings, and communications, whether written or oral.
          </Text>

          <Text className="text-white text-base font-bold mb-2">
            20. Contact
          </Text>
          <Text className="text-gray-300 text-sm leading-6 mb-4">
            If you have any questions or concerns about these Terms, please contact us at:{"\n\n"}
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
