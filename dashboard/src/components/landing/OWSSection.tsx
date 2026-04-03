import { useTranslation } from 'react-i18next'

/**
 * OWS (Open Wallet Standard) landing section.
 *
 * Highlights the agent wallet infrastructure — multi-chain,
 * encrypted keys, policy-gated signing via OWS.
 */
export function OWSSection() {
  const { t } = useTranslation()

  return (
    <section className="py-16 border-t border-gray-200">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <span className="inline-block px-3 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full uppercase tracking-wider mb-3">
            {t('landing.ows.badge', 'OWS 1.2')}
          </span>
          <h2 className="text-2xl sm:text-3xl font-black text-gray-900 mb-3">
            {t('landing.ows.title', 'Agent Wallet (OWS)')}
          </h2>
          <p className="text-gray-500 max-w-2xl mx-auto text-sm sm:text-base">
            {t(
              'landing.ows.subtitle',
              'Multi-chain wallet for AI agents. Encrypted keys, policy-gated signing, and on-chain identity — all local, never custodial.'
            )}
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Multi-Chain */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-base font-bold text-gray-900 mb-2">
              {t('landing.ows.features.multiChain.title', '8 Chains Supported')}
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed">
              {t(
                'landing.ows.features.multiChain.desc',
                'One wallet, all networks. Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, and Monad — ready out of the box.'
              )}
            </p>
          </div>

          {/* Card 2: Encrypted Keys */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-base font-bold text-gray-900 mb-2">
              {t('landing.ows.features.encrypted.title', 'AES-256-GCM Encrypted')}
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed">
              {t(
                'landing.ows.features.encrypted.desc',
                'Private keys are encrypted at rest and never leave the local vault. Signing decrypts in memory, signs, and wipes — zero exposure.'
              )}
            </p>
          </div>

          {/* Card 3: Policy-Gated Signing */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="text-base font-bold text-gray-900 mb-2">
              {t('landing.ows.features.policy.title', 'Policy-Gated Signing')}
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed">
              {t(
                'landing.ows.features.policy.desc',
                'Define spending limits, whitelist contracts, and restrict chains. Agents operate within guardrails — no blank-check signing.'
              )}
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
