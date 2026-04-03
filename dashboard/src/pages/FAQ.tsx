import { useTranslation } from 'react-i18next'

interface FAQItem {
  key: string
}

interface FAQCategory {
  categoryKey: string
  items: FAQItem[]
}

const FAQ_DATA: FAQCategory[] = [
  {
    categoryKey: 'gettingStarted',
    items: [
      { key: 'whatIsEM' },
      { key: 'howToStart' },
      { key: 'needCrypto' },
      { key: 'requirements' },
    ],
  },
  {
    categoryKey: 'payments',
    items: [
      { key: 'howPaid' },
      { key: 'whenPaid' },
      { key: 'withdraw' },
      { key: 'fees' },
    ],
  },
  {
    categoryKey: 'tasks',
    items: [
      { key: 'taskTypes' },
      { key: 'howApply' },
      { key: 'evidenceRequired' },
    ],
  },
  {
    categoryKey: 'disputes',
    items: [
      { key: 'taskRejected' },
      { key: 'whatDispute' },
      { key: 'howDispute' },
      { key: 'disputeTime' },
      { key: 'disputeWin' },
    ],
  },
  {
    categoryKey: 'erc8128',
    items: [
      { key: 'whatIsERC8128' },
      { key: 'howERC8128Works' },
      { key: 'erc8128VsApiKeys' },
    ],
  },
  {
    categoryKey: 'a2a',
    items: [
      { key: 'whatIsA2A' },
      { key: 'howA2AWorks' },
      { key: 'a2aReputation' },
    ],
  },
  {
    categoryKey: 'h2a',
    items: [
      { key: 'whatIsH2A' },
      { key: 'howH2AWorks' },
      { key: 'h2aPricing' },
    ],
  },
  {
    categoryKey: 'worldId',
    items: [
      { key: 'whatIsWorldId' },
      { key: 'whyWorldId' },
      { key: 'howVerifyWorldId' },
      { key: 'orbVsDevice' },
    ],
  },
]

/**
 * FAQEntry — Always-visible Q&A pair (no accordion/collapsible).
 * Avoids text wrapping issues from accordion animations.
 */
function FAQEntry({ questionKey }: { questionKey: string }) {
  const { t } = useTranslation()

  return (
    <div className="py-4 px-1 border-b border-gray-100 last:border-b-0">
      <h3 className="text-sm font-medium text-gray-900 mb-2">
        {t(`help.faq.${questionKey}.q`)}
      </h3>
      <p className="text-sm text-gray-600 leading-relaxed">
        {t(`help.faq.${questionKey}.a`)}
      </p>
    </div>
  )
}

export function FAQ() {
  const { t } = useTranslation()

  return (
    <>
      {/* Hero */}
        <section className="bg-gray-900 text-white">
          <div className="max-w-3xl mx-auto px-4 py-16 text-center">
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight mb-3">
              {t('help.faq.title', 'Frequently Asked Questions')}
            </h1>
            <p className="text-gray-400 text-base sm:text-lg max-w-xl mx-auto">
              {t(
                'help.faq.subtitle',
                'Everything you need to know about earning on Execution Market'
              )}
            </p>
          </div>
        </section>

        {/* FAQ Categories */}
        <section className="max-w-3xl mx-auto px-4 py-12">
          <div className="space-y-10">
            {FAQ_DATA.map((category) => (
              <div key={category.categoryKey}>
                {/* Category Header */}
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-lg font-bold text-gray-900">
                    {t(`help.categories.${category.categoryKey}`)}
                  </h2>
                  <div className="flex-1 h-px bg-gray-200" />
                </div>

                {/* Questions — always visible, no accordion */}
                <div className="bg-gray-50 rounded-xl border border-gray-200 px-5">
                  {category.items.map((item) => (
                    <FAQEntry key={item.key} questionKey={item.key} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Still Need Help CTA */}
        <section className="bg-gray-50 border-t border-gray-200">
          <div className="max-w-3xl mx-auto px-4 py-14 text-center">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {t('help.stillNeedHelp.title', 'Still have questions?')}
            </h2>
            <p className="text-gray-600 text-sm mb-6">
              {t(
                'help.stillNeedHelp.subtitle',
                'Our support team is ready to help'
              )}
            </p>
            <a
              href="mailto:UltravioletaDAO@gmail.com"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-500 text-white text-sm font-semibold rounded-lg hover:bg-emerald-400 transition-colors"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
              {t('help.contactEmail', 'Email')}
            </a>
          </div>
        </section>
    </>
  )
}
