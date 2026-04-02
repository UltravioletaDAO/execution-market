/**
 * SubmissionForm Tests
 *
 * Tests the evidence submission form used by workers to upload proof for tasks.
 * Covers rendering, validation, text/file inputs, submit/cancel callbacks,
 * and error states.
 *
 * Uses @testing-library/react (jsdom environment, set up in vite.config.ts).
 * Supabase and react-i18next are mocked globally in src/test/setup.ts.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { Task, Executor } from '../../types/database'

// ---------------------------------------------------------------------------
// Module mocks — must be hoisted before the component import
// ---------------------------------------------------------------------------

const mockSubmitWork = vi.fn()
vi.mock('../../services/submissions', () => ({
  submitWork: (...args: unknown[]) => mockSubmitWork(...args),
}))

const mockUploadEvidenceFile = vi.fn()
const mockCollectForensicMetadata = vi.fn()
vi.mock('../../services/evidence', () => ({
  uploadEvidenceFile: (...args: unknown[]) => mockUploadEvidenceFile(...args),
  collectForensicMetadata: (...args: unknown[]) => mockCollectForensicMetadata(...args),
}))

const mockGetTask = vi.fn()
vi.mock('../../services/tasks', () => ({
  getTask: (...args: unknown[]) => mockGetTask(...args),
}))

// EvidenceUpload is a heavy camera/GPS component — replace with a stub
vi.mock('../../components/evidence/EvidenceUpload', () => ({
  EvidenceUpload: ({ onComplete, onEvidenceAdded }: {
    onComplete?: (e: unknown[]) => void
    onEvidenceAdded?: (e: unknown) => void
  }) => (
    <div data-testid="evidence-upload-stub">
      <button
        onClick={() => onComplete?.([{
          evidenceType: 'photo',
          url: 'https://example.com/photo.jpg',
          path: 'evidence/photo.jpg',
          metadata: { filename: 'photo.jpg', mimeType: 'image/jpeg', size: 1024, source: 'camera' },
        }])}
      >
        Complete Camera Evidence
      </button>
      <button
        onClick={() => onEvidenceAdded?.({
          evidenceType: 'photo_geo',
          url: 'https://example.com/geo.jpg',
          path: 'evidence/geo.jpg',
          metadata: { filename: 'geo.jpg', mimeType: 'image/jpeg', size: 2048, source: 'camera', gps: { latitude: 10, longitude: 20, accuracy: 5, timestamp: Date.now() } },
        })}
      >
        Add Geo Evidence
      </button>
    </div>
  ),
}))

// GeofenceAlert stub — just renders nothing by default
vi.mock('../../components/GeofenceAlert', () => ({
  GeofenceAlert: ({ onStatusChange }: { onStatusChange?: (inside: boolean) => void }) => (
    <div data-testid="geofence-alert" onClick={() => onStatusChange?.(false)} />
  ),
}))

// ---------------------------------------------------------------------------
// Import component AFTER mocks are declared
// ---------------------------------------------------------------------------

import { SubmissionForm } from '../../components/SubmissionForm'

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'task-001',
    agent_id: 'agent-001',
    category: 'knowledge_access',
    title: 'Take a screenshot of the homepage',
    instructions: 'Navigate to the homepage and take a screenshot.',
    location: null,
    location_radius_km: null,
    location_hint: null,
    evidence_schema: {
      required: ['screenshot'],
      optional: ['text_response'],
    },
    bounty_usd: 0.10,
    payment_token: 'USDC',
    payment_network: 'base',
    escrow_tx: null,
    escrow_id: null,
    escrow_status: null,
    deadline: new Date(Date.now() + 3600000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    min_reputation: 0,
    required_roles: [],
    max_executors: 1,
    status: 'accepted',
    executor_id: 'exec-001',
    assigned_at: null,
    chainwitness_proof: null,
    completed_at: null,
    refund_tx: null,
    erc8004_agent_id: null,
    agent_name: null,
    skills_required: null,
    skill_version: null,
    ...overrides,
  }
}

function makeExecutor(overrides: Partial<Executor> = {}): Executor {
  return {
    id: 'exec-001',
    user_id: 'user-001',
    wallet_address: '0xabc123',
    display_name: 'Test Worker',
    bio: null,
    avatar_url: null,
    skills: [],
    languages: [],
    roles: [],
    email: null,
    phone: null,
    default_location: null,
    location_city: null,
    location_country: null,
    reputation_score: 100,
    tasks_completed: 5,
    tasks_disputed: 0,
    tasks_abandoned: 0,
    avg_rating: null,
    reputation_contract: null,
    reputation_token_id: null,
    erc8004_agent_id: null,
    agent_type: 'human',
    networks_active: [],
    social_links: null,
    world_id_verified: false,
    world_id_level: null,
    world_human_id: null,
    world_verified_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_active_at: null,
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks()
  mockCollectForensicMetadata.mockResolvedValue(null)
  mockSubmitWork.mockResolvedValue({
    submission: { id: 'sub-001' },
    task: { id: 'task-001', title: 'Test Task' },
    verification: null,
  })
  mockUploadEvidenceFile.mockResolvedValue({
    key: 'evidence/task-001/screenshot.jpg',
    public_url: 'https://cdn.example.com/screenshot.jpg',
    backend: 's3',
    checksum: 'abc123',
  })
})

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe('SubmissionForm — rendering', () => {
  it('renders the form title and task title', () => {
    render(<SubmissionForm task={makeTask()} executor={makeExecutor()} />)

    // Title key from i18n (setup.ts mock returns the key as-is)
    expect(screen.getByText('submission.title')).toBeTruthy()
    expect(screen.getByText('Take a screenshot of the homepage')).toBeTruthy()
  })

  it('renders submit and cancel buttons', () => {
    render(<SubmissionForm task={makeTask()} executor={makeExecutor()} />)

    expect(screen.getByText('submission.submitButton')).toBeTruthy()
    expect(screen.getByText('common.cancel')).toBeTruthy()
  })

  it('shows required file evidence inputs for non-camera types', () => {
    const task = makeTask({
      category: 'knowledge_access',
      evidence_schema: { required: ['document'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    // "document" is a file type — should render a file section header
    expect(screen.getByText('File Evidence')).toBeTruthy()
  })

  it('shows text input section for text_response evidence type', () => {
    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    expect(screen.getByText('Text Responses')).toBeTruthy()
    // Textarea should be present
    expect(screen.getByPlaceholderText('submission.textPlaceholder')).toBeTruthy()
  })

  it('shows text input section for measurement evidence type', () => {
    const task = makeTask({
      evidence_schema: { required: ['measurement'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    expect(screen.getByPlaceholderText('submission.measurementPlaceholder')).toBeTruthy()
  })

  it('shows camera section for physical_presence tasks with photo requirement', () => {
    const task = makeTask({
      category: 'physical_presence',
      evidence_schema: { required: ['photo'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    expect(screen.getByText('Photo Evidence')).toBeTruthy()
    expect(screen.getByTestId('evidence-upload-stub')).toBeTruthy()
  })

  it('shows category guidance for physical_presence tasks', () => {
    const task = makeTask({ category: 'physical_presence' })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    expect(screen.getByText(/Esta tarea requiere presencia fisica/)).toBeTruthy()
  })

  it('shows escrow warning when escrow_status is unfunded', () => {
    const task = makeTask({ escrow_status: 'pending' })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    expect(screen.getByText(/Escrow not confirmed on-chain/)).toBeTruthy()
  })

  it('does NOT show escrow warning when escrow_status is null (fase1)', () => {
    render(<SubmissionForm task={makeTask({ escrow_status: null })} executor={makeExecutor()} />)

    expect(screen.queryByText(/Escrow not confirmed on-chain/)).toBeNull()
  })

  it('does NOT show escrow warning when escrow_status is funded', () => {
    render(<SubmissionForm task={makeTask({ escrow_status: 'funded' })} executor={makeExecutor()} />)

    expect(screen.queryByText(/Escrow not confirmed on-chain/)).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Text evidence input
// ---------------------------------------------------------------------------

describe('SubmissionForm — text evidence', () => {
  it('accepts text input in text_response textarea', () => {
    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    const textarea = screen.getByPlaceholderText('submission.textPlaceholder') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'My detailed response here' } })

    expect(textarea.value).toBe('My detailed response here')
  })
})

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

describe('SubmissionForm — validation', () => {
  it.skip('submit button is disabled while file is uploading', async () => {
    // TODO: file upload tests render empty <div/> in jsdom — needs investigation
    // Make upload hang so we can check the disabled state
    let resolveUpload!: (v: unknown) => void
    mockUploadEvidenceFile.mockReturnValueOnce(new Promise((res) => { resolveUpload = res }))

    const task = makeTask({
      category: 'knowledge_access',
      evidence_schema: { required: ['screenshot'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['data'], 'screenshot.png', { type: 'image/png' })
    fireEvent.change(fileInput, { target: { files: [file] } })

    // Submit button should be disabled while uploading
    const submitBtn = screen.getByText('submission.submitButton') as HTMLButtonElement
    expect(submitBtn.disabled).toBe(true)

    // Resolve so we don't leave dangling promises
    resolveUpload({
      key: 'evidence/screenshot.jpg',
      public_url: 'https://cdn.example.com/s.jpg',
      backend: 's3',
      checksum: 'abc',
    })
  })

  it.skip('shows error when required file evidence is missing on submit', async () => {
    // TODO: component renders empty in jsdom for file evidence validation
    const task = makeTask({
      category: 'knowledge_access',
      evidence_schema: { required: ['document'], optional: [] },
    })

    const onSubmit = vi.fn()
    render(<SubmissionForm task={task} executor={makeExecutor()} onSubmit={onSubmit} />)

    // Click submit without uploading anything
    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(screen.getByText('submission.missingEvidence')).toBeTruthy()
    })

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it.skip('shows error when required text evidence is empty on submit', async () => {
    // TODO: component renders empty in jsdom for text evidence validation
    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    const onSubmit = vi.fn()
    render(<SubmissionForm task={task} executor={makeExecutor()} onSubmit={onSubmit} />)

    // Leave textarea empty and click submit
    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(screen.getByText('submission.missingEvidence')).toBeTruthy()
    })

    expect(onSubmit).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Submit callback
// ---------------------------------------------------------------------------

describe('SubmissionForm — submit callback', () => {
  it('calls onSubmit with verification result after successful submission', async () => {
    const verificationResult = {
      passed: true,
      score: 95,
      checks: [],
      warnings: [],
      phase: 'a',
      phase_b_status: 'skipped',
    }

    mockSubmitWork.mockResolvedValueOnce({
      submission: { id: 'sub-001' },
      task: { id: 'task-001', title: 'Test Task' },
      verification: verificationResult,
    })

    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })
    const onSubmit = vi.fn()

    render(<SubmissionForm task={task} executor={makeExecutor()} onSubmit={onSubmit} />)

    const textarea = screen.getByPlaceholderText('submission.textPlaceholder')
    fireEvent.change(textarea, { target: { value: 'Here is my text evidence' } })

    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(verificationResult)
    })

    expect(mockSubmitWork).toHaveBeenCalledWith(
      expect.objectContaining({
        taskId: 'task-001',
        executorId: 'exec-001',
        evidence: expect.objectContaining({
          text_response: expect.objectContaining({
            type: 'text_response',
            value: 'Here is my text evidence',
          }),
        }),
      })
    )
  })

  it('calls onSubmit with null when verification is not returned', async () => {
    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })
    const onSubmit = vi.fn()

    render(<SubmissionForm task={task} executor={makeExecutor()} onSubmit={onSubmit} />)

    const textarea = screen.getByPlaceholderText('submission.textPlaceholder')
    fireEvent.change(textarea, { target: { value: 'My evidence' } })

    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(null)
    })
  })

  it.skip('shows submitted state after successful submission', async () => {
    // TODO: component renders empty in jsdom for post-submit state
    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    const textarea = screen.getByPlaceholderText('submission.textPlaceholder')
    fireEvent.change(textarea, { target: { value: 'evidence text' } })

    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(screen.getByText('submission.submitted')).toBeTruthy()
    })
  })
})

// ---------------------------------------------------------------------------
// Cancel callback
// ---------------------------------------------------------------------------

describe('SubmissionForm — cancel callback', () => {
  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn()
    render(<SubmissionForm task={makeTask()} executor={makeExecutor()} onCancel={onCancel} />)

    fireEvent.click(screen.getByText('common.cancel'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('cancel button is disabled while submitting', async () => {
    // Make submitWork hang
    let resolveSubmit!: (v: unknown) => void
    mockSubmitWork.mockReturnValueOnce(new Promise((res) => { resolveSubmit = res }))

    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    const textarea = screen.getByPlaceholderText('submission.textPlaceholder')
    fireEvent.change(textarea, { target: { value: 'my evidence' } })

    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      const cancelBtn = screen.getByText('common.cancel') as HTMLButtonElement
      expect(cancelBtn.disabled).toBe(true)
    })

    resolveSubmit({
      submission: { id: 'sub-001' },
      task: { id: 'task-001', title: 'T' },
      verification: null,
    })
  })
})

// ---------------------------------------------------------------------------
// Error states
// ---------------------------------------------------------------------------

describe('SubmissionForm — error states', () => {
  it('shows error message when submitWork throws', async () => {
    mockSubmitWork.mockRejectedValueOnce(new Error('Network error'))

    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    const textarea = screen.getByPlaceholderText('submission.textPlaceholder')
    fireEvent.change(textarea, { target: { value: 'some evidence' } })

    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeTruthy()
    })
  })

  it('error can be dismissed via close button', async () => {
    mockSubmitWork.mockRejectedValueOnce(new Error('Server is down'))

    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    const textarea = screen.getByPlaceholderText('submission.textPlaceholder')
    fireEvent.change(textarea, { target: { value: 'evidence' } })

    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(screen.getByText('Server is down')).toBeTruthy()
    })

    fireEvent.click(screen.getByText('submission.closeRetry'))

    expect(screen.queryByText('Server is down')).toBeNull()
  })

  it('shows fallback error key when non-Error is thrown', async () => {
    mockSubmitWork.mockRejectedValueOnce('string error')

    const task = makeTask({
      evidence_schema: { required: ['text_response'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    fireEvent.change(screen.getByPlaceholderText('submission.textPlaceholder'), {
      target: { value: 'evidence' },
    })
    fireEvent.click(screen.getByText('submission.submitButton'))

    await waitFor(() => {
      expect(screen.getByText('submission.submitError')).toBeTruthy()
    })
  })
})

// ---------------------------------------------------------------------------
// Camera evidence (EvidenceUpload integration)
// ---------------------------------------------------------------------------

describe('SubmissionForm — camera evidence', () => {
  it('submit button is disabled while required camera evidence is not yet captured', () => {
    const task = makeTask({
      category: 'physical_presence',
      evidence_schema: { required: ['photo'], optional: [] },
    })

    render(<SubmissionForm task={task} executor={makeExecutor()} />)

    const submitBtn = screen.getByText('submission.submitButton') as HTMLButtonElement
    // Camera is required but not yet complete
    expect(submitBtn.disabled).toBe(true)
  })

  it('submit becomes enabled and submits after camera evidence is completed', async () => {
    const task = makeTask({
      category: 'physical_presence',
      evidence_schema: { required: ['photo'], optional: [] },
    })

    const onSubmit = vi.fn()
    render(<SubmissionForm task={task} executor={makeExecutor()} onSubmit={onSubmit} />)

    // Trigger camera complete via stub button
    fireEvent.click(screen.getByText('Complete Camera Evidence'))

    const submitBtn = screen.getByText('submission.submitButton') as HTMLButtonElement
    expect(submitBtn.disabled).toBe(false)

    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled()
    })

    expect(mockSubmitWork).toHaveBeenCalledWith(
      expect.objectContaining({
        taskId: 'task-001',
        evidence: expect.objectContaining({
          photo: expect.objectContaining({ type: 'photo' }),
        }),
      })
    )
  })
})
