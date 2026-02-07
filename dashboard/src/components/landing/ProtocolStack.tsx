import { useTranslation } from 'react-i18next'

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
    name: 'ERC-8004',
    standard: 'Identity Registry',
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
    url: 'https://github.com/BackTrackCo/',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
      </svg>
    ),
  },
]

const networks = [
  { name: 'Base', logo: '/base.png' },
  { name: 'Ethereum', logo: '/ethereum.png' },
  { name: 'Polygon', logo: '/polygon.png' },
  { name: 'Arbitrum', logo: '/arbitrum.png' },
  { name: 'Celo', logo: '/celo.png' },
  { name: 'Monad', logo: '/monad.png' },
  { name: 'Avalanche', logo: '/avalanche.png' },
]

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

        {/* Network strip */}
        <div className="mt-6 pt-5 border-t border-gray-800">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <p className="text-xs md:text-sm font-semibold text-white">
                {t('landing.protocolStack.networksTitle', '7 EVM Networks')}
              </p>
              <p className="text-[10px] md:text-xs text-gray-500">
                {t('landing.protocolStack.networksSubtitle', 'x402 payments + x402r escrow + ERC-8004 identity')}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {networks.map((net) => (
                <div key={net.name} className="group/net relative">
                  <img
                    src={net.logo}
                    alt={net.name}
                    className="w-6 h-6 md:w-7 md:h-7 rounded-full ring-1 ring-gray-700 group-hover/net:ring-emerald-500/50 transition-all opacity-70 group-hover/net:opacity-100"
                  />
                  <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[9px] text-gray-500 opacity-0 group-hover/net:opacity-100 transition-opacity whitespace-nowrap">
                    {net.name}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Status line */}
          <div className="mt-4 flex items-center justify-between text-[10px] md:text-xs text-gray-600">
            <span>USDC &middot; EURC &middot; USDT &middot; PYUSD &middot; AUSD</span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              {t('landing.protocolStack.status', 'Live')}
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
