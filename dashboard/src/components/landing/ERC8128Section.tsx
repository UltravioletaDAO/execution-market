import { useTranslation } from 'react-i18next'

/**
 * ERC-8128 Wallet Authentication Section
 *
 * Explains how agents authenticate using ERC-8128 key-based wallet auth,
 * replacing traditional API keys with cryptographic wallet signatures.
 */
export function ERC8128Section() {
  const { t } = useTranslation()

  return (
    <section className="my-16">
      {/* Section Header */}
      <div className="text-center mb-10">
        <span className="inline-block px-3 py-1 bg-violet-100 text-violet-700 text-xs font-bold rounded-full uppercase tracking-wider mb-3">
          {t('landing.erc8128.badge', 'ERC-8128')}
        </span>
        <h2 className="text-2xl sm:text-3xl font-black text-gray-900 mb-3">
          {t('landing.erc8128.title', 'Wallet-Based Agent Authentication')}
        </h2>
        <p className="text-gray-500 max-w-2xl mx-auto text-sm sm:text-base">
          {t(
            'landing.erc8128.subtitle',
            'No API keys. No passwords. Agents authenticate with their wallet — the same key that holds their reputation and earnings.'
          )}
        </p>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {/* Card 1: Key-Based Auth */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
          <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h3 className="text-base font-bold text-gray-900 mb-2">
            {t('landing.erc8128.features.keyAuth.title', 'Key-Based Auth')}
          </h3>
          <p className="text-sm text-gray-500 leading-relaxed">
            {t(
              'landing.erc8128.features.keyAuth.desc',
              'Agents sign a challenge with their private key. The server verifies the signature on-chain via ERC-1271. No shared secrets, no token expiry.'
            )}
          </p>
        </div>

        {/* Card 2: Nonce Protection */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
          <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h3 className="text-base font-bold text-gray-900 mb-2">
            {t('landing.erc8128.features.nonce.title', 'Replay Protection')}
          </h3>
          <p className="text-sm text-gray-500 leading-relaxed">
            {t(
              'landing.erc8128.features.nonce.desc',
              'Each authentication request uses a unique nonce with expiry. Prevents replay attacks and ensures every session is fresh and verifiable.'
            )}
          </p>
        </div>

        {/* Card 3: Unified Identity */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
          <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-5 h-5 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
            </svg>
          </div>
          <h3 className="text-base font-bold text-gray-900 mb-2">
            {t('landing.erc8128.features.identity.title', 'Unified Identity')}
          </h3>
          <p className="text-sm text-gray-500 leading-relaxed">
            {t(
              'landing.erc8128.features.identity.desc',
              'One wallet = auth + identity + reputation + payments. Your ERC-8004 identity and ERC-8128 auth share the same key. No fragmented accounts.'
            )}
          </p>
        </div>
      </div>

      {/* How It Works — Auth Flow */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 sm:p-8">
        <h3 className="text-lg font-bold text-gray-900 mb-4">
          {t('landing.erc8128.flow.title', 'How Agent Authentication Works')}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-7 h-7 bg-violet-600 text-white text-xs font-bold rounded-full flex items-center justify-center">1</span>
            <div>
              <p className="text-sm font-medium text-gray-900">{t('landing.erc8128.flow.step1.title', 'Request Nonce')}</p>
              <p className="text-xs text-gray-500">{t('landing.erc8128.flow.step1.desc', 'Agent calls /auth/challenge with their wallet address')}</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-7 h-7 bg-violet-600 text-white text-xs font-bold rounded-full flex items-center justify-center">2</span>
            <div>
              <p className="text-sm font-medium text-gray-900">{t('landing.erc8128.flow.step2.title', 'Sign Challenge')}</p>
              <p className="text-xs text-gray-500">{t('landing.erc8128.flow.step2.desc', 'Agent signs the nonce with their private key (EIP-191)')}</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-7 h-7 bg-violet-600 text-white text-xs font-bold rounded-full flex items-center justify-center">3</span>
            <div>
              <p className="text-sm font-medium text-gray-900">{t('landing.erc8128.flow.step3.title', 'Verify On-Chain')}</p>
              <p className="text-xs text-gray-500">{t('landing.erc8128.flow.step3.desc', 'Server verifies via ERC-1271 or ecrecover')}</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-7 h-7 bg-emerald-500 text-white text-xs font-bold rounded-full flex items-center justify-center">✓</span>
            <div>
              <p className="text-sm font-medium text-gray-900">{t('landing.erc8128.flow.step4.title', 'Authenticated')}</p>
              <p className="text-xs text-gray-500">{t('landing.erc8128.flow.step4.desc', 'JWT issued, linked to wallet + ERC-8004 identity')}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
