import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { AppHeader } from '../components/layout/AppHeader'
import { AppFooter } from '../components/layout/AppFooter'

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
]

function AccordionItem({
  questionKey,
  isOpen,
  onToggle,
}: {
  questionKey: string
  isOpen: boolean
  onToggle: () => void
}) {
  const { t } = useTranslation()

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-4 py-4 px-1 text-left group"
        aria-expanded={isOpen}
      >
        <span className="text-sm font-medium text-gray-900 group-hover:text-emerald-600 transition-colors">
          {t(`help.faq.${questionKey}.q`)}
        </span>
        <svg
          className={`w-5 h-5 flex-shrink-0 text-gray-400 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ease-in-out ${
          isOpen ? 'max-h-96 opacity-100 pb-4' : 'max-h-0 opacity-0'
        }`}
      >
        <p className="text-sm text-gray-600 leading-relaxed px-1">
          {t(`help.faq.${questionKey}.a`)}
        </p>
      </div>
    </div>
  )
}

export function FAQ() {
  const { t } = useTranslation()
  const { openAuthModal } = useAuth()
  const [openItem, setOpenItem] = useState<string | null>(null)

  const handleToggle = (key: string) => {
    setOpenItem((prev) => (prev === key ? null : key))
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <AppHeader onConnectWallet={openAuthModal} />

      <main className="flex-1">
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

                {/* Questions */}
                <div className="bg-gray-50 rounded-xl border border-gray-200 px-5">
                  {category.items.map((item) => (
                    <AccordionItem
                      key={item.key}
                      questionKey={item.key}
                      isOpen={openItem === item.key}
                      onToggle={() => handleToggle(item.key)}
                    />
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
      </main>

      <AppFooter />
    </div>
  )
}
