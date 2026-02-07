import { useTranslation } from 'react-i18next'

const protocols = [
  {
    key: 'x402',
    name: 'x402',
    standard: 'HTTP 402',
  },
  {
    key: 'erc8004',
    name: 'ERC-8004',
    standard: 'Identity Registry',
  },
  {
    key: 'x402r',
    name: 'x402r',
    standard: 'Escrow',
  },
]

export function ProtocolStack() {
  const { t } = useTranslation()

  return (
    <section className="bg-gray-900 -mx-4 px-4 py-5 md:py-6 my-6 md:my-8">
      <div className="max-w-4xl mx-auto">
        {/* Section label */}
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] md:text-xs font-bold uppercase tracking-[0.2em] text-gray-500">
            {t('landing.protocolStack.label', 'Protocol Stack')}
          </span>
        </div>

        {/* Protocol cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
          {protocols.map((protocol) => (
            <div
              key={protocol.key}
              className="border-l-2 border-emerald-500 pl-3 md:pl-4 py-1"
            >
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-base md:text-lg font-black text-white tracking-tight">
                  {protocol.name}
                </span>
                <span className="text-[10px] md:text-xs text-gray-500 uppercase tracking-wider">
                  {t(`landing.protocolStack.${protocol.key}.standard`, protocol.standard)}
                </span>
              </div>
              <p className="text-xs md:text-sm text-gray-400 leading-relaxed">
                {t(`landing.protocolStack.${protocol.key}.description`)}
              </p>
            </div>
          ))}
        </div>

        {/* Bottom line */}
        <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-[10px] md:text-xs text-gray-600">
          <span>{t('landing.protocolStack.network', 'Base Mainnet')} &middot; USDC</span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {t('landing.protocolStack.status', 'Live')}
          </span>
        </div>
      </div>
    </section>
  )
}
