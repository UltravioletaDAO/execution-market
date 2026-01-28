/**
 * HelpPage - FAQ, tutorials, and support
 *
 * Features:
 * - FAQ accordion
 * - Getting started guide
 * - Contact support
 * - Video tutorials (planned)
 */

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'

interface HelpPageProps {
  onBack: () => void
}

// FAQ item component
function FAQItem({
  question,
  answer,
  isOpen,
  onToggle,
}: {
  question: string
  answer: string
  isOpen: boolean
  onToggle: () => void
}) {
  return (
    <div className="border-b border-gray-100 last:border-0">
      <button
        onClick={onToggle}
        className="w-full px-4 py-4 flex items-center justify-between text-left"
      >
        <span className={`font-medium ${isOpen ? 'text-blue-600' : 'text-gray-900'}`}>
          {question}
        </span>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-4 pb-4 text-gray-600 text-sm animate-fade-in">
          {answer}
        </div>
      )}
    </div>
  )
}

export function HelpPage({ onBack }: HelpPageProps) {
  const { t } = useTranslation()
  const [openFAQ, setOpenFAQ] = useState<number | null>(0)
  const [activeCategory, setActiveCategory] = useState<'getting-started' | 'payments' | 'tasks' | 'disputes'>('getting-started')

  // FAQ data by category
  const faqData = {
    'getting-started': [
      {
        question: t('help.faq.whatIsChamba.q', 'Que es Chamba?'),
        answer: t('help.faq.whatIsChamba.a', 'Chamba es una plataforma donde puedes ganar dinero completando tareas del mundo real para agentes de IA. Verificas cosas, recolectas datos, tomas fotos, y mas - todo desde tu celular.'),
      },
      {
        question: t('help.faq.howToStart.q', 'Como empiezo?'),
        answer: t('help.faq.howToStart.a', '1. Conecta tu billetera crypto (o crea una nueva con tu email). 2. Configura tu perfil y habilidades. 3. Navega las tareas disponibles. 4. Aplica a las que te interesen. 5. Completa el trabajo y envía tu evidencia. 6. Recibe tu pago en USDC!'),
      },
      {
        question: t('help.faq.needCrypto.q', 'Necesito saber de crypto?'),
        answer: t('help.faq.needCrypto.a', 'No! Si no tienes experiencia con crypto, te ayudamos a crear una billetera con solo tu email. Recibes tus pagos en USDC (una moneda estable que siempre vale $1 USD) y puedes retirar a tu banco local.'),
      },
      {
        question: t('help.faq.requirements.q', 'Que necesito para usar Chamba?'),
        answer: t('help.faq.requirements.a', 'Solo necesitas un smartphone con acceso a internet, camara, y GPS. Algunas tareas pueden requerir habilidades especificas (como hablar ingles o tener vehiculo), pero hay tareas para todos los perfiles.'),
      },
    ],
    payments: [
      {
        question: t('help.faq.howPaid.q', 'Como me pagan?'),
        answer: t('help.faq.howPaid.a', 'Cuando tu trabajo es aprobado, el pago se deposita automaticamente en tu billetera. Usamos USDC en la red Base para pagos instantáneos y baratos. Puedes ver tu saldo en tu perfil.'),
      },
      {
        question: t('help.faq.whenPaid.q', 'Cuanto tarda el pago?'),
        answer: t('help.faq.whenPaid.a', 'Una vez aprobado tu trabajo, el pago es instantáneo (segundos, no días). La revisión del agente puede tardar entre minutos y 24 horas dependiendo de la tarea.'),
      },
      {
        question: t('help.faq.withdraw.q', 'Como retiro mi dinero?'),
        answer: t('help.faq.withdraw.a', 'Puedes retirar tus USDC a cualquier otra billetera, exchange, o usar servicios que convierten crypto a tu moneda local. El retiro minimo es $5 USDC.'),
      },
      {
        question: t('help.faq.fees.q', 'Hay comisiones?'),
        answer: t('help.faq.fees.a', 'Chamba cobra una pequeña comisión por cada tarea completada (ya incluida en el precio que ves). Los retiros tienen un costo de red muy bajo (~$0.01 en Base).'),
      },
    ],
    tasks: [
      {
        question: t('help.faq.taskTypes.q', 'Que tipos de tareas hay?'),
        answer: t('help.faq.taskTypes.a', 'Hay muchos tipos: verificar que un negocio existe, tomar fotos de productos, completar encuestas, mystery shopping, recolectar datos de precios, entregas, traducciones, y más. Cada tarea tiene instrucciones claras.'),
      },
      {
        question: t('help.faq.howApply.q', 'Como aplico a una tarea?'),
        answer: t('help.faq.howApply.a', 'Busca tareas en tu area o que coincidan con tus habilidades. Haz clic en una tarea para ver los detalles. Si te interesa, presiona "Aplicar". El agente revisará tu perfil y te asignará si eres un buen match.'),
      },
      {
        question: t('help.faq.evidenceRequired.q', 'Que evidencia necesito enviar?'),
        answer: t('help.faq.evidenceRequired.a', 'Depende de la tarea. Generalmente necesitas fotos tomadas en el momento (con GPS y timestamp), respuestas a preguntas específicas, y a veces archivos adicionales. Las instrucciones de cada tarea son muy claras.'),
      },
      {
        question: t('help.faq.taskRejected.q', 'Que pasa si rechazan mi trabajo?'),
        answer: t('help.faq.taskRejected.a', 'Si no estás de acuerdo con un rechazo, puedes abrir una disputa. Un mediador humano revisará la evidencia de ambas partes y tomará una decisión final.'),
      },
    ],
    disputes: [
      {
        question: t('help.faq.whatDispute.q', 'Que es una disputa?'),
        answer: t('help.faq.whatDispute.a', 'Una disputa es cuando no estás de acuerdo con el rechazo de tu trabajo. Puedes presentar evidencia adicional y un mediador neutral revisará el caso.'),
      },
      {
        question: t('help.faq.howDispute.q', 'Como abro una disputa?'),
        answer: t('help.faq.howDispute.a', 'Ve a "Mis Tareas" > encuentra la tarea rechazada > presiona "Disputar". Describe tu posición y sube cualquier evidencia que apoye tu caso. Tienes 48 horas después del rechazo para abrir una disputa.'),
      },
      {
        question: t('help.faq.disputeTime.q', 'Cuanto tarda resolver una disputa?'),
        answer: t('help.faq.disputeTime.a', 'Las disputas se resuelven tipicamente en 24-72 horas. Recibirás una notificación cuando haya una decisión.'),
      },
      {
        question: t('help.faq.disputeWin.q', 'Que pasa si gano la disputa?'),
        answer: t('help.faq.disputeWin.a', 'Si el mediador decide a tu favor, recibes el pago completo de la tarea. Tu reputación no se ve afectada por el rechazo inicial.'),
      },
    ],
  }

  // Toggle FAQ item
  const toggleFAQ = useCallback((index: number) => {
    setOpenFAQ(openFAQ === index ? null : index)
  }, [openFAQ])

  // Category tabs
  const categories: { id: typeof activeCategory; label: string; icon: string }[] = [
    { id: 'getting-started', label: t('help.categories.gettingStarted', 'Primeros pasos'), icon: '🚀' },
    { id: 'payments', label: t('help.categories.payments', 'Pagos'), icon: '💰' },
    { id: 'tasks', label: t('help.categories.tasks', 'Tareas'), icon: '📋' },
    { id: 'disputes', label: t('help.categories.disputes', 'Disputas'), icon: '⚖️' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-4 py-4 flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold text-gray-900">
            {t('help.title', 'Ayuda')}
          </h1>
        </div>
      </div>

      <div className="p-4 space-y-6 pb-20">
        {/* Quick actions */}
        <div className="grid grid-cols-2 gap-3">
          <a
            href="mailto:soporte@chamba.app"
            className="flex flex-col items-center gap-2 p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="text-sm font-medium text-gray-900">
              {t('help.contactEmail', 'Email')}
            </span>
          </a>

          <a
            href="https://t.me/chambasoporte"
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col items-center gap-2 p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
              </svg>
            </div>
            <span className="text-sm font-medium text-gray-900">
              {t('help.contactTelegram', 'Telegram')}
            </span>
          </a>
        </div>

        {/* Getting started guide */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <span className="text-xl">📖</span>
            </div>
            <div>
              <h2 className="font-medium text-gray-900">
                {t('help.quickGuide.title', 'Guia rapida')}
              </h2>
              <p className="text-sm text-gray-500">
                {t('help.quickGuide.subtitle', 'Completa tu primera tarea en 5 minutos')}
              </p>
            </div>
          </div>

          <div className="p-4">
            <ol className="space-y-4">
              {[
                { step: 1, title: t('help.quickGuide.step1.title', 'Configura tu perfil'), desc: t('help.quickGuide.step1.desc', 'Agrega tu nombre y habilidades') },
                { step: 2, title: t('help.quickGuide.step2.title', 'Busca tareas'), desc: t('help.quickGuide.step2.desc', 'Filtra por ubicacion y categoria') },
                { step: 3, title: t('help.quickGuide.step3.title', 'Aplica a una tarea'), desc: t('help.quickGuide.step3.desc', 'Lee las instrucciones y presiona Aplicar') },
                { step: 4, title: t('help.quickGuide.step4.title', 'Completa el trabajo'), desc: t('help.quickGuide.step4.desc', 'Sigue las instrucciones y toma fotos') },
                { step: 5, title: t('help.quickGuide.step5.title', 'Recibe tu pago'), desc: t('help.quickGuide.step5.desc', 'El pago llega automaticamente a tu billetera') },
              ].map(({ step, title, desc }) => (
                <li key={step} className="flex gap-4">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-blue-600">{step}</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{title}</p>
                    <p className="text-sm text-gray-500">{desc}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* FAQ section */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">
              {t('help.faq.title', 'Preguntas frecuentes')}
            </h2>
          </div>

          {/* Category tabs */}
          <div className="px-4 py-3 border-b border-gray-100 overflow-x-auto scrollbar-hide">
            <div className="flex gap-2">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => {
                    setActiveCategory(cat.id)
                    setOpenFAQ(0)
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
                    activeCategory === cat.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span>{cat.icon}</span>
                  <span>{cat.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* FAQ items */}
          <div>
            {faqData[activeCategory].map((item, index) => (
              <FAQItem
                key={index}
                question={item.question}
                answer={item.answer}
                isOpen={openFAQ === index}
                onToggle={() => toggleFAQ(index)}
              />
            ))}
          </div>
        </section>

        {/* Still need help */}
        <section className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-6 text-white text-center">
          <h3 className="font-semibold text-lg mb-2">
            {t('help.stillNeedHelp.title', 'Todavia tienes dudas?')}
          </h3>
          <p className="text-blue-100 mb-4 text-sm">
            {t('help.stillNeedHelp.subtitle', 'Nuestro equipo de soporte esta listo para ayudarte')}
          </p>
          <a
            href="mailto:soporte@chamba.app"
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-white text-blue-600 font-medium rounded-lg hover:bg-blue-50 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            {t('help.contactSupport', 'Contactar soporte')}
          </a>
        </section>
      </div>
    </div>
  )
}

export default HelpPage
