/**
 * ProfileCompletionModal Tests
 *
 * Verifies the onboarding modal:
 * - Renders for new users (no pre-filled data)
 * - Pre-fills from existing executor data
 * - Does NOT pre-fill auto-generated Worker_XXXX names
 * - Validates required fields (display_name + bio)
 * - Calls onComplete/onSkip callbacks
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock useDynamicContext BEFORE importing the component
vi.mock('@dynamic-labs/sdk-react-core', () => ({
  useDynamicContext: () => ({ user: null }),
}))

// Mock useProfileUpdate BEFORE importing the component
const mockUpdateProfile = vi.fn()
vi.mock('../../hooks/useProfileUpdate', () => ({
  useProfileUpdate: () => ({
    updateProfile: mockUpdateProfile,
    saving: false,
    error: null,
  }),
}))

import { ProfileCompletionModal } from '../../components/ProfileCompletionModal'

describe('ProfileCompletionModal', () => {
  const mockOnComplete = vi.fn()
  const mockOnSkip = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUpdateProfile.mockResolvedValue(true)
  })

  // --------------------------------------------------------------------------
  // Rendering
  // --------------------------------------------------------------------------

  it('renders the modal with title and form fields', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    expect(screen.getByText('Complete Your Profile')).toBeTruthy()
    expect(screen.getByPlaceholderText(/e\.g\. Maria/i)).toBeTruthy()
    expect(screen.getByPlaceholderText(/Tell agents about/i)).toBeTruthy()
  })

  it('shows skip button when onSkip is provided', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} onSkip={mockOnSkip} />
    )

    expect(screen.getByText('Skip')).toBeTruthy()
  })

  it('does not show skip button when onSkip is not provided', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    expect(screen.queryByText('Skip')).toBeNull()
  })

  // --------------------------------------------------------------------------
  // Pre-filling from executor
  // --------------------------------------------------------------------------

  it('pre-fills form from existing executor data', () => {
    const executor = {
      display_name: '0xultravioleta',
      bio: 'openclaw builder',
      skills: ['photography', 'delivery'],
      languages: ['Spanish', 'English'],
      location_city: 'Miami',
      location_country: 'USA',
      email: 'test@example.com',
    }

    render(
      <ProfileCompletionModal
        onComplete={mockOnComplete}
        executor={executor}
      />
    )

    // Display name should be pre-filled
    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i) as HTMLInputElement
    expect(nameInput.value).toBe('0xultravioleta')

    // Bio should be pre-filled
    const bioInput = screen.getByPlaceholderText(/Tell agents about/i) as HTMLTextAreaElement
    expect(bioInput.value).toBe('openclaw builder')
  })

  it('does NOT pre-fill auto-generated Worker_XXXX names', () => {
    const executor = {
      display_name: 'Worker_e4dc963c',
      bio: null,
      skills: null,
      languages: null,
      location_city: null,
      location_country: null,
      email: null,
    }

    render(
      <ProfileCompletionModal
        onComplete={mockOnComplete}
        executor={executor}
      />
    )

    // Name input should be EMPTY — Worker_XXXX is not a real name
    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i) as HTMLInputElement
    expect(nameInput.value).toBe('')
  })

  it('does NOT pre-fill Worker_AABBCCDD (uppercase hex)', () => {
    render(
      <ProfileCompletionModal
        onComplete={mockOnComplete}
        executor={{ display_name: 'Worker_AABB1122' }}
      />
    )

    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i) as HTMLInputElement
    expect(nameInput.value).toBe('')
  })

  it('pre-fills when executor has no display_name (null)', () => {
    render(
      <ProfileCompletionModal
        onComplete={mockOnComplete}
        executor={{ display_name: null, bio: 'some bio' }}
      />
    )

    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i) as HTMLInputElement
    expect(nameInput.value).toBe('')
  })

  // --------------------------------------------------------------------------
  // Validation
  // --------------------------------------------------------------------------

  it('submit button is disabled when display_name is empty', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    const submitBtn = screen.getByText('Complete Profile')
    expect(submitBtn).toBeDisabled()
  })

  it('submit button is disabled when bio is empty', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i)
    fireEvent.change(nameInput, { target: { value: 'Test User' } })

    const submitBtn = screen.getByText('Complete Profile')
    expect(submitBtn).toBeDisabled()
  })

  it('submit button is enabled when both name and bio are filled', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i)
    fireEvent.change(nameInput, { target: { value: 'Test User' } })

    const bioInput = screen.getByPlaceholderText(/Tell agents about/i)
    fireEvent.change(bioInput, { target: { value: 'I do tasks' } })

    const submitBtn = screen.getByText('Complete Profile')
    expect(submitBtn).not.toBeDisabled()
  })

  // --------------------------------------------------------------------------
  // Submission
  // --------------------------------------------------------------------------

  it('calls updateProfile and onComplete on successful submit', async () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i)
    fireEvent.change(nameInput, { target: { value: 'Test User' } })

    const bioInput = screen.getByPlaceholderText(/Tell agents about/i)
    fireEvent.change(bioInput, { target: { value: 'I do great work' } })

    const submitBtn = screen.getByText('Complete Profile')
    fireEvent.click(submitBtn)

    // Wait for the full async chain: handleSubmit → updateProfile → onComplete
    await vi.waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledTimes(1)
    })

    expect(mockUpdateProfile).toHaveBeenCalledTimes(1)
    const callArgs = mockUpdateProfile.mock.calls[0][0]
    expect(callArgs.display_name).toBe('Test User')
    expect(callArgs.bio).toBe('I do great work')
  })

  it('does NOT call onComplete when updateProfile fails', async () => {
    mockUpdateProfile.mockResolvedValueOnce(false)

    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    const nameInput = screen.getByPlaceholderText(/e\.g\. Maria/i)
    fireEvent.change(nameInput, { target: { value: 'Test User' } })

    const bioInput = screen.getByPlaceholderText(/Tell agents about/i)
    fireEvent.change(bioInput, { target: { value: 'Bio here' } })

    fireEvent.click(screen.getByText('Complete Profile'))

    await vi.waitFor(() => {
      expect(mockUpdateProfile).toHaveBeenCalledTimes(1)
    })

    expect(mockOnComplete).not.toHaveBeenCalled()
  })

  it('calls onSkip when skip button is clicked', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} onSkip={mockOnSkip} />
    )

    fireEvent.click(screen.getByText('Skip'))
    expect(mockOnSkip).toHaveBeenCalledTimes(1)
  })

  // --------------------------------------------------------------------------
  // Skills toggle
  // --------------------------------------------------------------------------

  it('toggles predefined skill chips', () => {
    render(
      <ProfileCompletionModal onComplete={mockOnComplete} />
    )

    const photographyBtn = screen.getByText('photography')
    fireEvent.click(photographyBtn)

    // Should now have selected styling (blue)
    expect(photographyBtn.className).toContain('bg-blue-50')

    // Click again to deselect
    fireEvent.click(photographyBtn)
    expect(photographyBtn.className).not.toContain('bg-blue-50')
  })
})
