/**
 * RelayChainStatus — visual tracker for multi-worker relay chains.
 *
 * Shows: chain progress, per-leg worker info, handoff timestamps,
 * and payment status in a visual pipeline format.
 */

import React from "react";

interface RelayLeg {
  leg_id: string;
  leg_number: number;
  worker_wallet: string | null;
  worker_nick: string | null;
  status: string;
  pickup_location: { lat?: number; lng?: number; address?: string } | null;
  dropoff_location: { lat?: number; lng?: number; address?: string } | null;
  bounty_usdc: number;
  picked_up_at: string | null;
  handed_off_at: string | null;
}

interface RelayChain {
  chain_id: string;
  parent_task_id: string;
  status: string;
  total_legs: number;
  completed_legs: number;
  legs: RelayLeg[];
}

interface Props {
  chain: RelayChain;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-200 text-gray-700",
  assigned: "bg-blue-100 text-blue-700",
  in_transit: "bg-yellow-100 text-yellow-700",
  handed_off: "bg-green-100 text-green-700",
  completed: "bg-green-200 text-green-800",
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Waiting",
  assigned: "Ready",
  in_transit: "In Transit",
  handed_off: "Handed Off",
  completed: "Done",
  failed: "Failed",
};

function truncateWallet(wallet: string | null): string {
  if (!wallet) return "—";
  if (wallet.length <= 10) return wallet;
  return `${wallet.slice(0, 6)}...${wallet.slice(-4)}`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString();
}

export function RelayChainStatus({ chain }: Props) {
  const progress = chain.total_legs > 0
    ? Math.round((chain.completed_legs / chain.total_legs) * 100)
    : 0;

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">
            Relay Chain {chain.chain_id.slice(0, 8)}
          </h3>
          <p className="text-sm text-gray-500">
            Task: {chain.parent_task_id.slice(0, 8)} · {chain.status}
          </p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold">{progress}%</span>
          <p className="text-xs text-gray-500">
            {chain.completed_legs}/{chain.total_legs} legs
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className="bg-green-500 h-2 rounded-full transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Legs */}
      <div className="space-y-2">
        {chain.legs.map((leg, idx) => (
          <div
            key={leg.leg_id}
            className="flex items-center gap-3 p-3 rounded border border-gray-100"
          >
            {/* Leg number */}
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-bold">
              {leg.leg_number}
            </div>

            {/* Status badge */}
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[leg.status] || STATUS_COLORS.pending}`}
            >
              {STATUS_LABELS[leg.status] || leg.status}
            </span>

            {/* Worker */}
            <span className="text-sm">
              {leg.worker_nick || truncateWallet(leg.worker_wallet)}
            </span>

            {/* Bounty */}
            <span className="text-sm font-medium ml-auto">
              ${leg.bounty_usdc.toFixed(2)}
            </span>

            {/* Handoff time */}
            {leg.handed_off_at && (
              <span className="text-xs text-gray-400">
                {formatTime(leg.handed_off_at)}
              </span>
            )}

            {/* Connector arrow (not on last leg) */}
            {idx < chain.legs.length - 1 && (
              <span className="text-gray-300 text-lg">→</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
