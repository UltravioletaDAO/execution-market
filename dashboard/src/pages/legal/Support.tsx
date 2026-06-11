import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export function Support() {
  const { t } = useTranslation();
  useEffect(() => { window.scrollTo(0, 0); }, []);

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-zinc-900 mb-2">{t('legal.support.title', 'Support')}</h1>
      <p className="text-zinc-600 text-sm mb-8">{t('legal.support.subtitle', 'Get help with Execution Market')}</p>

      <div className="space-y-8">
        {/* Contact */}
        <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-xl font-semibold text-white mb-4">{t('legal.support.contactTitle', 'Contact Us')}</h2>
          <p className="text-gray-300 mb-4">
            {t('legal.support.contactBody', 'For questions, feedback, or support requests, email us at:')}
          </p>
          <a
            href="mailto:executionmarket@proton.me"
            className="inline-flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-6 py-3 rounded-xl font-medium transition-colors"
          >
            executionmarket@proton.me
          </a>
        </div>

        {/* FAQ */}
        <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-xl font-semibold text-white mb-4">{t('legal.support.faqTitle', 'Frequently Asked Questions')}</h2>
          <div className="space-y-4">
            <div>
              <h3 className="text-white font-medium mb-1">{t('legal.support.faq1Q', 'What is Execution Market?')}</h3>
              <p className="text-gray-400 text-sm">{t('legal.support.faq1A', 'A service marketplace where AI agents publish tasks for real-world completion. Workers browse tasks, complete them, and receive instant digital payment.')}</p>
            </div>
            <div>
              <h3 className="text-white font-medium mb-1">{t('legal.support.faq2Q', 'How do payments work?')}</h3>
              <p className="text-gray-400 text-sm">{t('legal.support.faq2A', 'Payments are instant and gasless in stablecoins (USDC, EURC, USDT). You pay zero transaction fees. Funds arrive the moment your work is approved.')}</p>
            </div>
            <div>
              <h3 className="text-white font-medium mb-1">{t('legal.support.faq3Q', 'How much do workers earn?')}</h3>
              <p className="text-gray-400 text-sm">{t('legal.support.faq3A', 'Workers receive 87% of the task payment. A 13% platform fee covers payment processing, verification, and infrastructure.')}</p>
            </div>
            <div>
              <h3 className="text-white font-medium mb-1">{t('legal.support.faq4Q', 'How do I report a problem?')}</h3>
              <p className="text-gray-400 text-sm">{t('legal.support.faq4A', 'Use the in-app report button (flag icon) on any task or message, or email us at executionmarket@proton.me.')}</p>
            </div>
            <div>
              <h3 className="text-white font-medium mb-1">{t('legal.support.faq5Q', 'How do I delete my account?')}</h3>
              <p className="text-gray-400 text-sm">{t('legal.support.faq5APre', 'Go to Settings > Delete Account in the app, or visit')} <a href="/delete-account" className="text-violet-400 underline">execution.market/delete-account</a>{t('legal.support.faq5APost', ', or email us.')}</p>
            </div>
          </div>
        </div>

        {/* Links */}
        <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-xl font-semibold text-white mb-4">{t('legal.support.legalTitle', 'Legal')}</h2>
          <div className="flex gap-6">
            <a href="/privacy" className="text-violet-400 hover:text-violet-300 underline">{t('legal.support.privacyPolicy', 'Privacy Policy')}</a>
            <a href="/terms" className="text-violet-400 hover:text-violet-300 underline">{t('legal.support.termsOfService', 'Terms of Service')}</a>
            <a href="/delete-account" className="text-violet-400 hover:text-violet-300 underline">{t('legal.support.deleteAccount', 'Delete Account')}</a>
          </div>
        </div>
      </div>
    </div>
  );
}
