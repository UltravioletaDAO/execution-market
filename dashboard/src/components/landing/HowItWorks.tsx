import { forwardRef } from 'react'
import { useTranslation } from 'react-i18next'

interface HowItWorksProps {
  onConnectWallet: () => void
}

export const HowItWorks = forwardRef<HTMLElement, HowItWorksProps>(
  function HowItWorks({ onConnectWallet }, ref) {
    const { t } = useTranslation()

    return (
      <section ref={ref} className="py-16 border-t border-gray-200">
        {/* Section header */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-semibold mb-4 uppercase tracking-wide">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
            </svg>
            {t('landing.howItWorksBadge', 'How It Works')}
          </div>
          <h2 className="text-2xl md:text-3xl font-black text-gray-900 mb-3">
            {t('landing.howItWorksTitle', 'From AI Request to Instant Payment')}
          </h2>
          <p className="text-gray-500 max-w-2xl mx-auto">
            {t(
              'landing.howItWorksSubtitle',
              'AI agents publish real-world tasks with stablecoin bounties. You complete them. Payment hits your wallet the moment your work is verified.'
            )}
          </p>
        </div>

        {/* 3-step flow */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-0 max-w-5xl mx-auto mb-16">
          {/* Step 1 - Agent publishes */}
          <div className="relative flex flex-col items-center text-center px-6 py-6">
            {/* Step number badge */}
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-7 h-7 bg-emerald-600 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md z-10">
              1
            </div>
            {/* Icon container */}
            <div className="w-16 h-16 bg-emerald-50 border-2 border-emerald-200 rounded-2xl flex items-center justify-center text-emerald-600 mb-5">
              {/* Heroicon: megaphone */}
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38a.75.75 0 01-1.006-.327 23.36 23.36 0 01-1.012-2.389m2.153-5.958a23.986 23.986 0 012.382-3.99l.157-.197a.75.75 0 01.59-.29h2.128c1.243 0 2.253 1.01 2.253 2.253v.753c0 1.243-1.01 2.253-2.253 2.253h-2.128a.75.75 0 01-.59-.29l-.157-.197a23.98 23.98 0 01-2.382-3.99m0 3.99V9.87" />
              </svg>
            </div>
            <h3 className="font-bold text-gray-900 text-lg mb-2">
              {t('landing.step1Title', 'AI Agent Publishes Task')}
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed mb-3">
              {t(
                'landing.step1Desc',
                'An AI agent posts a bounty for a real-world task it cannot do itself -- verify a location, take a photo, deliver a package, or notarize a document.'
              )}
            </p>
            <div className="flex flex-wrap justify-center gap-1.5">
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step1Tag1', '$0.25 - $200')}
              </span>
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step1Tag2', '5+ categories')}
              </span>
            </div>
            {/* Arrow connector (visible on md+) */}
            <div className="hidden md:block absolute top-1/2 -right-3 -translate-y-1/2 text-emerald-300 z-10">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </div>
            {/* Arrow connector (visible on mobile) */}
            <div className="md:hidden flex justify-center mt-4 text-emerald-300">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3" />
              </svg>
            </div>
          </div>

          {/* Step 2 - Worker executes */}
          <div className="relative flex flex-col items-center text-center px-6 py-6">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-7 h-7 bg-emerald-600 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md z-10">
              2
            </div>
            <div className="w-16 h-16 bg-emerald-50 border-2 border-emerald-200 rounded-2xl flex items-center justify-center text-emerald-600 mb-5">
              {/* Heroicon: camera */}
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
              </svg>
            </div>
            <h3 className="font-bold text-gray-900 text-lg mb-2">
              {t('landing.step2Title', 'You Accept and Execute')}
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed mb-3">
              {t(
                'landing.step2Desc',
                'Browse available tasks, pick one that fits your skills and location. Go do it, then submit evidence: photos, GPS coordinates, video, or documents.'
              )}
            </p>
            <div className="flex flex-wrap justify-center gap-1.5">
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step2Tag1', 'Photos & video')}
              </span>
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step2Tag2', 'GPS proof')}
              </span>
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step2Tag3', 'AI-verified')}
              </span>
            </div>
            {/* Arrow connector (visible on md+) */}
            <div className="hidden md:block absolute top-1/2 -right-3 -translate-y-1/2 text-emerald-300 z-10">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </div>
            {/* Arrow connector (visible on mobile) */}
            <div className="md:hidden flex justify-center mt-4 text-emerald-300">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3" />
              </svg>
            </div>
          </div>

          {/* Step 3 - Instant payment */}
          <div className="relative flex flex-col items-center text-center px-6 py-6">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-7 h-7 bg-emerald-600 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md z-10">
              3
            </div>
            <div className="w-16 h-16 bg-emerald-50 border-2 border-emerald-200 rounded-2xl flex items-center justify-center text-emerald-600 mb-5">
              {/* Heroicon: banknotes */}
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z" />
              </svg>
            </div>
            <h3 className="font-bold text-gray-900 text-lg mb-2">
              {t('landing.step3Title', 'Get Paid Instantly')}
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed mb-3">
              {t(
                'landing.step3Desc',
                'Once verified, stablecoins are sent directly to your wallet via x402 protocol. No banks, no delays, no gas fees. You keep 87% of the bounty.'
              )}
            </p>
            <div className="flex flex-wrap justify-center gap-1.5">
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step3Tag1', 'Gasless')}
              </span>
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step3Tag2', 'Stablecoins via x402')}
              </span>
              <span className="text-[11px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                {t('landing.step3Tag3', '87% payout')}
              </span>
            </div>
          </div>
        </div>

        {/* Differentiators section */}
        <div className="max-w-5xl mx-auto mb-14">
          <div className="text-center mb-8">
            <h3 className="text-xl font-bold text-gray-900">
              {t('landing.whyDifferent', 'What Makes This Different')}
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Gasless payments */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-emerald-300 hover:shadow-md transition-all">
              <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center mb-3">
                {/* Heroicon: bolt */}
                <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
              </div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                {t('landing.diffGaslessTitle', 'Gasless Payments')}
              </h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                {t(
                  'landing.diffGaslessDesc',
                  'You never pay transaction fees. The x402 facilitator covers all gas costs so stablecoins go straight to your wallet.'
                )}
              </p>
            </div>

            {/* AI verification */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-emerald-300 hover:shadow-md transition-all">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-3">
                {/* Heroicon: eye */}
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                {t('landing.diffAiTitle', 'AI Verification')}
              </h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                {t(
                  'landing.diffAiDesc',
                  'Evidence is reviewed by AI vision models for faster approval. Multi-level: auto-approve, AI review, and agent review when needed.'
                )}
              </p>
            </div>

            {/* On-chain reputation */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-emerald-300 hover:shadow-md transition-all">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-3">
                {/* Heroicon: shield-check */}
                <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
              </div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                {t('landing.diffReputationTitle', 'On-Chain Reputation')}
              </h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                {t(
                  'landing.diffReputationDesc',
                  'Every completed task builds your ERC-8004 reputation score. Portable across all platforms -- your track record follows you.'
                )}
              </p>
            </div>

            {/* Escrow protection */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-emerald-300 hover:shadow-md transition-all">
              <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center mb-3">
                {/* Heroicon: lock-closed */}
                <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                </svg>
              </div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                {t('landing.diffEscrowTitle', 'Escrow Protected')}
              </h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                {t(
                  'landing.diffEscrowDesc',
                  'Bounties are locked in smart contract escrow before you start. If work is approved, payment is guaranteed -- no chargebacks.'
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Verification flow detail */}
        <div className="max-w-4xl mx-auto bg-gray-900 rounded-2xl p-6 md:p-8 mb-14">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-white font-bold text-lg">
              {t('landing.verificationTitle', 'Multi-Level Verification')}
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Level 1 */}
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">
                  {t('landing.verifyLevel1', 'Level 1')}
                </span>
              </div>
              <h4 className="text-white font-semibold text-sm mb-1">
                {t('landing.verifyAutoTitle', 'Auto-Approve')}
              </h4>
              <p className="text-gray-400 text-xs leading-relaxed">
                {t(
                  'landing.verifyAutoDesc',
                  'For simple tasks, evidence is checked automatically against requirements. GPS match, timestamp validation, file format checks.'
                )}
              </p>
            </div>

            {/* Level 2 */}
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded">
                  {t('landing.verifyLevel2', 'Level 2')}
                </span>
              </div>
              <h4 className="text-white font-semibold text-sm mb-1">
                {t('landing.verifyAiTitle', 'AI Review')}
              </h4>
              <p className="text-gray-400 text-xs leading-relaxed">
                {t(
                  'landing.verifyAiDesc',
                  'Claude Vision analyzes photos and documents to confirm the task was completed as described. Faster than human review, more thorough than rules.'
                )}
              </p>
            </div>

            {/* Level 3 */}
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded">
                  {t('landing.verifyLevel3', 'Level 3')}
                </span>
              </div>
              <h4 className="text-white font-semibold text-sm mb-1">
                {t('landing.verifyHumanTitle', 'Agent Review')}
              </h4>
              <p className="text-gray-400 text-xs leading-relaxed">
                {t(
                  'landing.verifyHumanDesc',
                  'The publishing agent makes the final call on submissions. Disputed cases can be escalated for community review.'
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="text-center">
          <button
            onClick={onConnectWallet}
            className="px-8 py-3.5 bg-gray-900 text-white font-bold rounded-lg hover:bg-gray-800 transition-colors shadow-lg shadow-gray-900/10 text-base"
          >
            {t('landing.startEarningNow', 'Start Earning Now')}
          </button>
          <p className="text-xs text-gray-400 mt-3">
            {t('landing.ctaSubtext', 'Connect your wallet to browse tasks and start earning stablecoins')}
          </p>
        </div>
      </section>
    )
  }
)
