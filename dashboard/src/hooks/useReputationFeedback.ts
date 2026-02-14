/**
 * useReputationFeedback — Hook for worker direct on-chain reputation signing.
 *
 * State machine: idle → preparing → switching_chain → signing → confirming → complete | error
 *
 * The worker signs giveFeedback() directly from their wallet.
 * msg.sender on-chain = worker's address (trustless reputation).
 *
 * Pattern follows useEscrow.ts from same codebase.
 */

import { useState, useCallback } from 'react'
import { useAccount, useWriteContract, useWaitForTransactionReceipt, useSwitchChain } from 'wagmi'
import {
  REPUTATION_REGISTRY_ADDRESS,
  REPUTATION_REGISTRY_ABI,
  BASE_CHAIN_ID,
} from '../lib/contracts'
import {
  prepareFeedback,
  confirmFeedback,
  starsToScore,
  type PrepareFeedbackResponse,
} from '../services/reputation'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

export type FeedbackStep =
  | 'idle'
  | 'preparing'
  | 'switching_chain'
  | 'signing'
  | 'confirming'
  | 'complete'
  | 'error'

export interface FeedbackParams {
  agentId: number
  taskId: string
  stars: number // 1-5
  comment?: string
}

export interface UseReputationFeedbackReturn {
  step: FeedbackStep
  txHash: string | null
  error: string | null
  estimatedGas: number | null
  submitFeedback: (params: FeedbackParams) => Promise<void>
  reset: () => void
}

// --------------------------------------------------------------------------
// Hook
// --------------------------------------------------------------------------

export function useReputationFeedback(): UseReputationFeedbackReturn {
  const { address, chainId } = useAccount()
  const { switchChainAsync } = useSwitchChain()
  const { writeContractAsync } = useWriteContract()

  const [step, setStep] = useState<FeedbackStep>('idle')
  const [txHash, setTxHash] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [estimatedGas, setEstimatedGas] = useState<number | null>(null)

  // Watch for TX confirmation
  useWaitForTransactionReceipt({
    hash: txHash as `0x${string}` | undefined,
    query: {
      enabled: step === 'confirming' && !!txHash,
    },
  })

  const reset = useCallback(() => {
    setStep('idle')
    setTxHash(null)
    setError(null)
    setEstimatedGas(null)
  }, [])

  const submitFeedback = useCallback(
    async (params: FeedbackParams) => {
      if (!address) {
        setError('Wallet no conectada')
        setStep('error')
        return
      }

      const score = starsToScore(params.stars)

      try {
        // Phase 1: Prepare (backend persists S3 + returns params)
        setStep('preparing')
        setError(null)

        let prepared: PrepareFeedbackResponse
        try {
          prepared = await prepareFeedback({
            agent_id: params.agentId,
            task_id: params.taskId,
            score,
            comment: params.comment,
            worker_address: address,
          })
        } catch (err) {
          throw new Error(
            err instanceof Error
              ? err.message
              : 'Error preparando feedback'
          )
        }

        setEstimatedGas(prepared.estimated_gas)

        // Phase 2: Switch chain if needed
        if (chainId !== BASE_CHAIN_ID) {
          setStep('switching_chain')
          try {
            await switchChainAsync({ chainId: BASE_CHAIN_ID })
          } catch {
            throw new Error('Debes cambiar a la red Base para continuar')
          }
        }

        // Phase 3: Sign TX in wallet
        setStep('signing')

        // Convert feedbackHash to bytes32
        const hashHex = prepared.feedback_hash.startsWith('0x')
          ? prepared.feedback_hash
          : `0x${prepared.feedback_hash}`

        const hash = await writeContractAsync({
          address: REPUTATION_REGISTRY_ADDRESS,
          abi: REPUTATION_REGISTRY_ABI,
          functionName: 'giveFeedback',
          args: [
            BigInt(prepared.agent_id),
            BigInt(prepared.value),
            prepared.value_decimals,
            prepared.tag1,
            prepared.tag2,
            prepared.endpoint,
            prepared.feedback_uri,
            hashHex as `0x${string}`,
          ],
          chainId: BASE_CHAIN_ID,
        })

        setTxHash(hash)

        // Phase 4: Confirm (notify backend)
        setStep('confirming')

        try {
          await confirmFeedback({
            prepare_id: prepared.prepare_id,
            tx_hash: hash,
            task_id: params.taskId,
          })
        } catch {
          // Non-critical: TX is on-chain even if confirm fails
          console.warn('confirm-feedback call failed (TX already on-chain)')
        }

        setStep('complete')
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : 'Error desconocido'

        // User-friendly error messages
        if (msg.includes('User rejected') || msg.includes('user rejected')) {
          setError('Transaccion rechazada en la wallet')
        } else if (msg.includes('insufficient funds') || msg.includes('insufficient balance')) {
          setError('Sin gas suficiente (necesitas ETH en Base para la transaccion)')
        } else if (msg.includes('self-feedback')) {
          setError('No puedes calificarte a ti mismo')
        } else {
          setError(msg)
        }
        setStep('error')
      }
    },
    [address, chainId, switchChainAsync, writeContractAsync]
  )

  return {
    step,
    txHash,
    error,
    estimatedGas,
    submitFeedback,
    reset,
  }
}
