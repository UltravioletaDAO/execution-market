import { forwardRef } from 'react'
import { useTranslation } from 'react-i18next'

interface HowItWorksProps {
  onConnectWallet: () => void
}

export const HowItWorks = forwardRef<HTMLElement, HowItWorksProps>(
  function HowItWorks({ onConnectWallet }, ref) {
    const { t } = useTranslation()

    const steps = [
      {
        number: '1',
        title: t('landing.step1Title', 'Connect Your Wallet'),
        description: t('landing.step1Desc', 'Link your crypto wallet or create one with your email. It takes 30 seconds.'),
        icon: (
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a2.25 2.25 0 00-2.25-2.25H15a3 3 0 11-6 0H5.25A2.25 2.25 0 003 12m18 0v6a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 013 9m18 0V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 013 6v3" />
          </svg>
        ),
      },
      {
        number: '2',
        title: t('landing.step2Title', 'Apply to a Job'),
        description: t('landing.step2Desc', 'Browse tasks, pick one that fits your skills and location. Apply with one tap.'),
        icon: (
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zM12 2.25V4.5m5.834.166l-1.591 1.591M20.25 10.5H18M7.757 14.743l-1.59 1.59M6 10.5H3.75m4.007-4.243l-1.59-1.59" />
          </svg>
        ),
      },
      {
        number: '3',
        title: t('landing.step3Title', 'Get Paid Instantly'),
        description: t('landing.step3Desc', 'Complete the task, submit evidence, and get USDC sent directly to your wallet. No banks, no delays.'),
        icon: (
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z" />
          </svg>
        ),
      },
    ]

    return (
      <section ref={ref} className="py-12 border-t border-gray-200">
        <div className="text-center mb-10">
          <h2 className="text-xl md:text-2xl font-black text-gray-900 mb-2">
            {t('landing.howItWorks', 'How it Works')}
          </h2>
          <p className="text-gray-500 text-sm">
            {t('landing.howItWorksSubtitle', 'Start earning in 3 simple steps')}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {steps.map((step) => (
            <div key={step.number} className="text-center">
              <div className="w-14 h-14 bg-emerald-50 border-2 border-emerald-200 rounded-2xl flex items-center justify-center text-emerald-600 mx-auto mb-4">
                {step.icon}
              </div>
              <div className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">
                {t('landing.step', 'Step')} {step.number}
              </div>
              <h3 className="font-bold text-gray-900 mb-1.5">{step.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="text-center mt-10">
          <button
            onClick={onConnectWallet}
            className="px-8 py-3 bg-gray-900 text-white font-bold rounded-lg hover:bg-gray-800 transition-colors"
          >
            {t('landing.startEarningNow', 'Start Earning Now')}
          </button>
        </div>
      </section>
    )
  }
)
