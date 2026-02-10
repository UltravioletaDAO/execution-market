// Execution Market: Withdrawal Form Component
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useWithdrawal, type EarningsData } from '../../hooks/useProfile'

interface WithdrawalFormProps {
  executorId: string
  earnings: EarningsData | null
  walletAddress: string
  onSuccess: () => void
  onCancel: () => void
}

export function WithdrawalForm({
  executorId,
  earnings,
  walletAddress,
  onSuccess,
  onCancel,
}: WithdrawalFormProps) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState('')
  const [destination, setDestination] = useState(walletAddress)
  const [useMax, setUseMax] = useState(false)

  const { withdraw, loading, error, success } = useWithdrawal(executorId)

  const balance = earnings?.balance_usdc || 0
  const minWithdrawal = 1.00 // Minimum $1 USDC
  const networkFee = 0.50 // Estimated network fee

  // Calculate net amount
  const grossAmount = useMax ? balance : parseFloat(amount) || 0
  const netAmount = Math.max(0, grossAmount - networkFee)

  // Validate input
  const isValidAmount = grossAmount >= minWithdrawal && grossAmount <= balance
  const isValidAddress = /^0x[a-fA-F0-9]{40}$/.test(destination)
  const canSubmit = isValidAmount && isValidAddress && !loading

  // Handle max toggle
  useEffect(() => {
    if (useMax) {
      setAmount(balance.toFixed(2))
    }
  }, [useMax, balance])

  // Handle success
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => {
        onSuccess()
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [success, onSuccess])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    await withdraw(grossAmount, destination)
  }

  // Success state
  if (success) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl max-w-md w-full p-6 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {t('profile.withdrawalSuccess', 'Withdrawal Initiated!')}
          </h3>
          <p className="text-gray-600 text-sm mb-4">
            {t('profile.withdrawalProcessing', 'Your withdrawal is being processed. Funds will arrive in your wallet shortly.')}
          </p>
          <p className="text-blue-600 font-mono text-sm break-all">
            ${netAmount.toFixed(2)} USDC
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            {t('profile.withdrawFunds', 'Withdraw Funds')}
          </h3>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Balance display */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">
              {t('profile.availableBalance', 'Available Balance')}
            </div>
            <div className="text-2xl font-bold text-gray-900">
              ${balance.toFixed(2)} <span className="text-sm font-normal text-gray-500">USDC</span>
            </div>
          </div>

          {/* Amount input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.withdrawAmount', 'Amount to Withdraw')}
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
              <input
                type="number"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value)
                  setUseMax(false)
                }}
                placeholder="0.00"
                step="0.01"
                min={minWithdrawal}
                max={balance}
                disabled={useMax}
                className="w-full pl-8 pr-20 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50"
              />
              <button
                type="button"
                onClick={() => setUseMax(!useMax)}
                className={`absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  useMax
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                MAX
              </button>
            </div>
            {grossAmount > 0 && grossAmount < minWithdrawal && (
              <p className="text-red-500 text-xs mt-1">
                {t('profile.minWithdrawal', 'Minimum withdrawal is ${{min}}', { min: minWithdrawal.toFixed(2) })}
              </p>
            )}
            {grossAmount > balance && (
              <p className="text-red-500 text-xs mt-1">
                {t('profile.insufficientBalance', 'Insufficient balance')}
              </p>
            )}
          </div>

          {/* Destination address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.destinationAddress', 'Destination Address')}
            </label>
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="0x..."
              className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
            />
            {destination && !isValidAddress && (
              <p className="text-red-500 text-xs mt-1">
                {t('profile.invalidAddress', 'Invalid wallet address')}
              </p>
            )}
            <p className="text-gray-500 text-xs mt-1">
              {t('profile.baseNetwork', "Withdrawals are sent on your task's network")}
            </p>
          </div>

          {/* Fee breakdown */}
          {grossAmount > 0 && isValidAmount && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">{t('profile.amount', 'Amount')}</span>
                <span className="font-medium">${grossAmount.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">{t('profile.networkFee', 'Network Fee')}</span>
                <span className="text-red-600">-${networkFee.toFixed(2)}</span>
              </div>
              <div className="border-t border-gray-200 pt-2 flex justify-between">
                <span className="font-medium text-gray-900">{t('profile.youReceive', 'You Receive')}</span>
                <span className="font-bold text-green-600">${netAmount.toFixed(2)}</span>
              </div>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
              <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span>{error.message}</span>
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={!canSubmit}
            className={`w-full py-3 rounded-lg font-medium transition-all ${
              canSubmit
                ? 'bg-blue-600 text-white hover:bg-blue-700 active:scale-98'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('profile.processing', 'Processing...')}
              </span>
            ) : (
              t('profile.confirmWithdrawal', 'Confirm Withdrawal')
            )}
          </button>

          {/* Cancel link */}
          <button
            type="button"
            onClick={onCancel}
            className="w-full py-2 text-gray-600 text-sm hover:text-gray-900 transition-colors"
          >
            {t('common.cancel', 'Cancel')}
          </button>
        </form>
      </div>
    </div>
  )
}
