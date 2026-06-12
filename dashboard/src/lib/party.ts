/**
 * Party labels — resolve the counterparty noun for a task (Universal Hiring Matrix).
 *
 * Publishers can target any | human | agent | robot. Before assignment the
 * published target drives the label ("Searching for Human"); once an executor
 * is assigned, their actual executor_type wins ("Human Assigned"). Falls back
 * to the neutral 'executor' when the party is unknown or 'any'.
 *
 * Use with the i18n `party.*` keys: t(`party.${taskParty(task)}`)
 */
import type { Task } from '../types/database'

export type PartyKind = 'human' | 'agent' | 'robot' | 'executor'

const PARTIES: readonly string[] = ['human', 'agent', 'robot']

function asParty(value?: string | null): PartyKind | null {
  return value && PARTIES.includes(value) ? (value as PartyKind) : null
}

/** Party noun for a task: assigned executor's type wins; else the published target. */
export function taskParty(task: Pick<Task, 'target_executor_type' | 'executor'>): PartyKind {
  return asParty(task.executor?.executor_type) ?? asParty(task.target_executor_type) ?? 'executor'
}
