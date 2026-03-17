export interface Task {
  id: string;
  title: string;
  instructions: string;
  category: string;
  bounty_usdc: number;
  status: string;
  deadline: string;
  payment_network: string;
  agent_id?: string;
  agent_wallet?: string;
  executor_id?: string;
  executor_wallet?: string;
  evidence_requirements?: EvidenceRequirement[];
  created_at: string;
}

export interface EvidenceRequirement {
  type: "photo" | "gps" | "text" | "video" | "json_response";
  label: string;
  required: boolean;
}

export interface Executor {
  id: string;
  wallet_address: string;
  display_name: string | null;
  reputation_score: number;
  tasks_completed: number;
}

export interface PaymentEvent {
  id: string;
  task_id: string;
  amount: number;
  chain: string;
  tx_hash: string;
  event_type: string;
  created_at: string;
}

export interface ReputationScore {
  agent_id: string;
  average_score: number;
  total_ratings: number;
  recent_feedback: ReputationFeedback[];
}

export interface ReputationFeedback {
  score: number;
  comment?: string;
  from_address: string;
  created_at: string;
}
