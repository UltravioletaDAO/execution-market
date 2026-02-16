/**
 * OnboardingFlow - New executor onboarding wizard
 *
 * Steps:
 * 1. Welcome & language selection
 * 2. Connect wallet
 * 3. Basic profile (name, photo)
 * 4. Select skills
 * 5. Set location preferences
 * 6. Enable notifications
 * 7. First task tutorial
 */

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { SkillSelector } from './SkillSelector'
import { LocationFilter, type GPSCoordinates } from './LocationFilter'
import { usePWA } from '../hooks/usePWA'

// Types
interface OnboardingData {
  displayName: string
  walletAddress: string
  skills: string[]
  location: GPSCoordinates | null
  maxDistance: number
  notificationsEnabled: boolean
}

interface OnboardingFlowProps {
  initialWalletAddress?: string
  onComplete: (data: OnboardingData) => void
  onSkip?: () => void
}

const STEPS = [
  'welcome',
  'wallet',
  'profile',
  'skills',
  'location',
  'notifications',
  'complete',
] as const

type Step = typeof STEPS[number]

export function OnboardingFlow({
  initialWalletAddress,
  onComplete,
  onSkip,
}: OnboardingFlowProps) {
  const { t, i18n } = useTranslation()
  const { requestNotificationPermission, notificationPermission } = usePWA()

  const [currentStep, setCurrentStep] = useState<Step>(
    initialWalletAddress ? 'profile' : 'welcome'
  )
  const [data, setData] = useState<OnboardingData>({
    displayName: '',
    walletAddress: initialWalletAddress || '',
    skills: [],
    location: null,
    maxDistance: 25,
    notificationsEnabled: false,
  })

  // Update data
  const updateData = useCallback(<K extends keyof OnboardingData>(
    key: K,
    value: OnboardingData[K]
  ) => {
    setData((prev) => ({ ...prev, [key]: value }))
  }, [])

  // Navigation
  const goToStep = useCallback((step: Step) => {
    setCurrentStep(step)
  }, [])

  const nextStep = useCallback(() => {
    const currentIndex = STEPS.indexOf(currentStep)
    if (currentIndex < STEPS.length - 1) {
      setCurrentStep(STEPS[currentIndex + 1])
    }
  }, [currentStep])

  const prevStep = useCallback(() => {
    const currentIndex = STEPS.indexOf(currentStep)
    if (currentIndex > 0) {
      setCurrentStep(STEPS[currentIndex - 1])
    }
  }, [currentStep])

  // Handle language change — persist choice so it survives page reload
  const handleLanguageChange = useCallback((lang: string) => {
    i18n.changeLanguage(lang)
    localStorage.setItem('em-lang', lang)
  }, [i18n])

  // Handle notification permission
  const handleNotificationRequest = useCallback(async () => {
    const granted = await requestNotificationPermission()
    updateData('notificationsEnabled', granted)
    nextStep()
  }, [requestNotificationPermission, updateData, nextStep])

  // Handle complete
  const handleComplete = useCallback(() => {
    onComplete(data)
  }, [data, onComplete])

  // Progress
  const progress = ((STEPS.indexOf(currentStep) + 1) / STEPS.length) * 100

  // Render step content
  const renderStep = () => {
    switch (currentStep) {
      case 'welcome':
        return (
          <div className="text-center">
            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-4xl">👋</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-3">
              {t('onboarding.welcomeTitle', 'Bienvenido a Execution Market!')}
            </h1>
            <p className="text-gray-600 mb-8">
              {t('onboarding.welcomeSubtitle', 'Completa tareas, gana crypto. Empecemos a configurar tu perfil.')}
            </p>

            {/* Language selection */}
            <div className="mb-8">
              <p className="text-sm text-gray-500 mb-3">
                {t('onboarding.selectLanguage', 'Selecciona tu idioma')}
              </p>
              <div className="flex justify-center gap-3">
                <button
                  onClick={() => handleLanguageChange('es')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    i18n.language === 'es'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🇪🇸 Espanol
                </button>
                <button
                  onClick={() => handleLanguageChange('en')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    i18n.language === 'en'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🇺🇸 English
                </button>
                <button
                  onClick={() => handleLanguageChange('pt')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    i18n.language === 'pt'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🇧🇷 Portugues
                </button>
              </div>
            </div>

            <button
              onClick={nextStep}
              className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('onboarding.getStarted', 'Comenzar')}
            </button>
          </div>
        )

      case 'wallet':
        return (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {t('onboarding.walletTitle', 'Conecta tu billetera')}
            </h2>
            <p className="text-gray-600 mb-6">
              {t('onboarding.walletSubtitle', 'Necesitas una billetera para recibir pagos. Si no tienes una, te ayudamos a crearla.')}
            </p>

            <div className="space-y-3 mb-6">
              {/* MetaMask */}
              <button
                onClick={() => {
                  // TODO: Connect MetaMask
                  updateData('walletAddress', '0x...')
                  nextStep()
                }}
                className="w-full flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
              >
                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                  <span className="text-xl">🦊</span>
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium text-gray-900">MetaMask</p>
                  <p className="text-sm text-gray-500">
                    {t('onboarding.metamaskDesc', 'Conecta tu billetera existente')}
                  </p>
                </div>
                <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* WalletConnect */}
              <button
                onClick={() => {
                  // TODO: Connect WalletConnect
                  nextStep()
                }}
                className="w-full flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
              >
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-xl">🔗</span>
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium text-gray-900">WalletConnect</p>
                  <p className="text-sm text-gray-500">
                    {t('onboarding.walletConnectDesc', 'Escanea con tu billetera movil')}
                  </p>
                </div>
                <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* Create new */}
              <button
                onClick={() => {
                  // TODO: Create wallet with email
                  nextStep()
                }}
                className="w-full flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
              >
                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <span className="text-xl">✉️</span>
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium text-gray-900">
                    {t('onboarding.createWallet', 'Crear con email')}
                  </p>
                  <p className="text-sm text-gray-500">
                    {t('onboarding.createWalletDesc', 'Nuevo en crypto? Te creamos una billetera')}
                  </p>
                </div>
                <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            <p className="text-xs text-gray-500 text-center">
              {t('onboarding.walletInfo', 'Tu billetera es como tu cuenta bancaria digital. Solo tu tienes acceso a tus fondos.')}
            </p>
          </div>
        )

      case 'profile':
        return (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {t('onboarding.profileTitle', 'Tu perfil')}
            </h2>
            <p className="text-gray-600 mb-6">
              {t('onboarding.profileSubtitle', 'Como quieres que te llamen?')}
            </p>

            {/* Avatar placeholder */}
            <div className="flex justify-center mb-6">
              <button className="relative">
                <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center">
                  <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <span className="absolute bottom-0 right-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </span>
              </button>
            </div>

            {/* Name input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('onboarding.displayName', 'Nombre o apodo')}
              </label>
              <input
                type="text"
                value={data.displayName}
                onChange={(e) => updateData('displayName', e.target.value)}
                placeholder={t('onboarding.namePlaceholder', 'ej. Maria, El Rapido, JuanDev')}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-2">
                {t('onboarding.nameInfo', 'Esto es como los agentes veran tu perfil')}
              </p>
            </div>

            <button
              onClick={nextStep}
              disabled={!data.displayName.trim()}
              className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {t('common.continue', 'Continuar')}
            </button>
          </div>
        )

      case 'skills':
        return (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {t('onboarding.skillsTitle', 'Tus habilidades')}
            </h2>
            <p className="text-gray-600 mb-6">
              {t('onboarding.skillsSubtitle', 'Selecciona las habilidades que tienes. Esto nos ayuda a mostrarte tareas relevantes.')}
            </p>

            <SkillSelector
              selectedSkills={data.skills}
              onSkillsChange={(skills) => updateData('skills', skills)}
              maxSkills={15}
            />

            <div className="flex gap-3 mt-6">
              <button
                onClick={nextStep}
                className="flex-1 py-3 text-gray-600 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
              >
                {t('common.skip', 'Saltar')}
              </button>
              <button
                onClick={nextStep}
                className="flex-1 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('common.continue', 'Continuar')}
              </button>
            </div>
          </div>
        )

      case 'location':
        return (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {t('onboarding.locationTitle', 'Tu ubicacion')}
            </h2>
            <p className="text-gray-600 mb-6">
              {t('onboarding.locationSubtitle', 'Algunas tareas requieren estar en un lugar especifico. Habilita la ubicacion para ver tareas cerca de ti.')}
            </p>

            <LocationFilter
              maxDistance={100}
              initialDistance={data.maxDistance}
              onDistanceChange={(distance) => updateData('maxDistance', distance)}
              onLocationChange={(location) => updateData('location', location)}
              showLocationButton
            />

            <div className="flex gap-3 mt-6">
              <button
                onClick={nextStep}
                className="flex-1 py-3 text-gray-600 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
              >
                {t('common.skip', 'Saltar')}
              </button>
              <button
                onClick={nextStep}
                className="flex-1 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('common.continue', 'Continuar')}
              </button>
            </div>
          </div>
        )

      case 'notifications':
        return (
          <div className="text-center">
            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {t('onboarding.notificationsTitle', 'Notificaciones')}
            </h2>
            <p className="text-gray-600 mb-8">
              {t('onboarding.notificationsSubtitle', 'Recibe alertas cuando haya tareas nuevas que te interesen o cuando tus envios sean revisados.')}
            </p>

            {notificationPermission === 'granted' ? (
              <div className="flex items-center justify-center gap-2 text-green-600 mb-6">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>{t('onboarding.notificationsEnabled', 'Notificaciones habilitadas')}</span>
              </div>
            ) : notificationPermission === 'denied' ? (
              <div className="flex items-center justify-center gap-2 text-red-600 mb-6">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>{t('onboarding.notificationsDenied', 'Notificaciones bloqueadas en este navegador')}</span>
              </div>
            ) : null}

            <div className="space-y-3">
              {notificationPermission === 'default' && (
                <button
                  onClick={handleNotificationRequest}
                  className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {t('onboarding.enableNotifications', 'Habilitar notificaciones')}
                </button>
              )}
              <button
                onClick={nextStep}
                className={`w-full py-3 font-medium rounded-lg transition-colors ${
                  notificationPermission === 'default'
                    ? 'text-gray-600 border border-gray-300 hover:bg-gray-50'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {notificationPermission === 'default'
                  ? t('common.skip', 'Saltar')
                  : t('common.continue', 'Continuar')}
              </button>
            </div>
          </div>
        )

      case 'complete':
        return (
          <div className="text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {t('onboarding.completeTitle', 'Listo!')}
            </h2>
            <p className="text-gray-600 mb-8">
              {t('onboarding.completeSubtitle', 'Tu perfil esta configurado. Ahora puedes empezar a explorar tareas y ganar crypto.')}
            </p>

            {/* Summary */}
            <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
              <h3 className="font-medium text-gray-900 mb-3">
                {t('onboarding.summary', 'Resumen')}
              </h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('profile.name', 'Nombre')}</dt>
                  <dd className="font-medium text-gray-900">{data.displayName}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('profile.skills', 'Habilidades')}</dt>
                  <dd className="font-medium text-gray-900">{data.skills.length}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('profile.location', 'Ubicacion')}</dt>
                  <dd className="font-medium text-gray-900">
                    {data.location
                      ? t('onboarding.locationEnabled', 'Habilitada')
                      : t('onboarding.locationDisabled', 'No configurada')}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('profile.notifications', 'Notificaciones')}</dt>
                  <dd className="font-medium text-gray-900">
                    {data.notificationsEnabled
                      ? t('common.enabled', 'Habilitadas')
                      : t('common.disabled', 'Deshabilitadas')}
                  </dd>
                </div>
              </dl>
            </div>

            <button
              onClick={handleComplete}
              className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('onboarding.startExploring', 'Explorar tareas')}
            </button>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Progress bar */}
      <div className="fixed top-0 left-0 right-0 h-1 bg-gray-100 z-50">
        <div
          className="h-full bg-blue-600 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Skip button */}
      {onSkip && currentStep !== 'complete' && (
        <button
          onClick={onSkip}
          className="fixed top-4 right-4 text-gray-500 hover:text-gray-700 text-sm z-50"
        >
          {t('common.skip', 'Saltar')}
        </button>
      )}

      {/* Back button */}
      {currentStep !== 'welcome' && currentStep !== 'complete' && (
        <button
          onClick={prevStep}
          className="fixed top-4 left-4 p-2 text-gray-500 hover:text-gray-700 z-50"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      )}

      {/* Step content */}
      <div className="px-6 py-16 max-w-md mx-auto">
        {renderStep()}
      </div>

      {/* Step indicators */}
      <div className="fixed bottom-8 left-0 right-0 flex justify-center gap-2">
        {STEPS.map((step, index) => (
          <button
            key={step}
            onClick={() => index < STEPS.indexOf(currentStep) && goToStep(step)}
            disabled={index >= STEPS.indexOf(currentStep)}
            className={`w-2 h-2 rounded-full transition-colors ${
              step === currentStep
                ? 'bg-blue-600 w-6'
                : index < STEPS.indexOf(currentStep)
                ? 'bg-blue-300 hover:bg-blue-400'
                : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
    </div>
  )
}

export type { OnboardingData }
export default OnboardingFlow
