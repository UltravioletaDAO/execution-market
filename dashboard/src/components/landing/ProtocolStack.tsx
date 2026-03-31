import { useTranslation } from 'react-i18next'
import { NETWORKS } from '../../config/networks'

const stablecoins = [
  { key: 'usdc', name: 'USDC', fullName: 'USD Coin', logo: '/usdc.png' },
  { key: 'eurc', name: 'EURC', fullName: 'Euro Coin', logo: '/eurc.png' },
  { key: 'usdt', name: 'USDT', fullName: 'Tether USD', logo: '/usdt.png' },
  { key: 'pyusd', name: 'PYUSD', fullName: 'PayPal USD', logo: '/pyusd.png' },
  { key: 'ausd', name: 'AUSD', fullName: 'Agora Dollar', logo: '/ausd.png' },
]

const protocols = [
  {
    key: 'x402',
    name: 'x402',
    standard: 'HTTP 402',
    url: 'https://www.x402.org/',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    key: 'erc8004',
    name: '8004',
    standard: 'Identity & Reputation Registry',
    url: 'https://www.8004.org/',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
  },
  {
    key: 'x402r',
    name: 'x402r',
    standard: 'Programmable Escrow',
    url: 'https://x402r.org/',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
      </svg>
    ),
  },
]

// Network list derived from config/networks.ts (single source of truth)
const networks = NETWORKS

export function ProtocolStack() {
  const { t } = useTranslation()

  return (
    <section className="bg-gray-900 -mx-4 px-4 py-8 md:py-12 my-6 md:my-8">
      <div className="max-w-4xl mx-auto">
        {/* Section label */}
        <div className="flex items-center gap-2 mb-2">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] md:text-xs font-bold uppercase tracking-[0.2em] text-gray-500">
            {t('landing.protocolStack.label', 'Protocol Stack')}
          </span>
        </div>

        {/* Trustless headline */}
        <h2 className="text-xl md:text-2xl font-black text-white mb-1 tracking-tight">
          {t('landing.protocolStack.headline', 'Trustless Infrastructure')}
        </h2>
        <p className="text-sm md:text-base text-gray-400 mb-6 max-w-2xl">
          {t('landing.protocolStack.subheadline', 'Trustless Agents. Trustless Humans. Trustless Robots. — No intermediaries, no custody, no permission needed.')}
        </p>

        {/* Protocol cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
          {protocols.map((protocol) => (
            <a
              key={protocol.key}
              href={protocol.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group border border-gray-800 hover:border-emerald-500/50 rounded-lg p-4 transition-all hover:bg-gray-800/50"
            >
              <div className="flex items-center gap-2.5 mb-2">
                <span className="text-emerald-400 group-hover:text-emerald-300 transition-colors">
                  {protocol.icon}
                </span>
                <span className="text-base md:text-lg font-black text-white tracking-tight">
                  {protocol.name}
                </span>
                <span className="text-[10px] md:text-xs text-gray-500 uppercase tracking-wider">
                  {t(`landing.protocolStack.${protocol.key}.standard`, protocol.standard)}
                </span>
              </div>
              <p className="text-xs md:text-sm text-gray-400 leading-relaxed mb-3">
                {t(`landing.protocolStack.${protocol.key}.description`)}
              </p>
              <span className="inline-flex items-center gap-1 text-[10px] md:text-xs text-emerald-500 group-hover:text-emerald-400 font-medium transition-colors">
                {t('landing.protocolStack.learnMore', 'Learn more')}
                <svg className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </span>
            </a>
          ))}
        </div>

        {/* Network & stablecoin strip */}
        <div className="mt-6 pt-5 border-t border-gray-800">
          {/* Networks row */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <p className="text-xs md:text-sm font-semibold text-white">
                {t('landing.protocolStack.networksTitle', '9 Networks')}
              </p>
              <p className="text-[10px] md:text-xs text-gray-500">
                {t('landing.protocolStack.networksSubtitle', '9 Networks Live · Multi-stablecoin payments across all chains')}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {networks.map((net) => (
                <div key={net.name} className="group/net relative">
                  <img
                    src={net.logo}
                    alt={net.name}
                    className={`w-6 h-6 md:w-7 md:h-7 rounded-full ring-1 transition-all cursor-pointer ${
                      net.live
                        ? 'ring-emerald-500/50 opacity-100 group-hover/net:ring-emerald-400 group-hover/net:scale-110'
                        : 'ring-gray-700 opacity-40 group-hover/net:opacity-70 group-hover/net:ring-gray-600'
                    }`}
                  />
                  <span className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded bg-gray-800 text-[10px] text-gray-200 font-medium opacity-0 group-hover/net:opacity-100 transition-opacity whitespace-nowrap shadow-lg border border-gray-700 z-10">
                    {net.name}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Stablecoins row */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {stablecoins.map((coin) => (
                <div key={coin.key} className="group/coin relative">
                  <img
                    src={coin.logo}
                    alt={coin.name}
                    className="w-5 h-5 md:w-6 md:h-6 rounded-full ring-1 ring-gray-700 opacity-90 group-hover/coin:ring-emerald-500/50 group-hover/coin:opacity-100 group-hover/coin:scale-110 transition-all cursor-pointer"
                  />
                  <span className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded bg-gray-800 text-[10px] text-gray-200 font-medium opacity-0 group-hover/coin:opacity-100 transition-opacity whitespace-nowrap shadow-lg border border-gray-700 z-10">
                    {coin.fullName}
                  </span>
                </div>
              ))}
              <span className="text-[10px] md:text-xs text-gray-600 ml-1">
                {t('landing.protocolStack.configuredTokens', '5 stablecoins live')}
              </span>
            </div>
            <span className="flex items-center gap-1.5 text-[10px] md:text-xs text-gray-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              {t('landing.protocolStack.status', '9 Networks Live')}
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
