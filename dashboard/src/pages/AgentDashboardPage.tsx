import { useCallback, Suspense, lazy } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const AgentDashboard = lazy(() => import('./AgentDashboard').then(m => ({ default: m.AgentDashboard })))
const SubmissionReviewModal = lazy(() => import('../components/SubmissionReviewModal').then(m => ({ default: m.SubmissionReviewModal })))

export function AgentDashboardPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { executor } = useAuth()

  const reviewSubmissionId = searchParams.get('review')

  const closeReview = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('review')
      return next
    })
  }, [setSearchParams])

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 py-6">
        <AgentDashboard
          agentId={executor?.id ?? ''}
          onBack={() => navigate('/')}
          onCreateTask={() => navigate('/agent/tasks/new')}
          onViewTask={(task) => navigate(`/agent/tasks?view=${task.id}`)}
          onReviewSubmission={(submission) => setSearchParams({ review: submission.id })}
        />
      </div>
      {reviewSubmissionId && (
        <Suspense fallback={null}>
          <SubmissionReviewModal
            submissionId={reviewSubmissionId}
            onClose={closeReview}
            onSuccess={closeReview}
          />
        </Suspense>
      )}
    </>
  )
}

export default AgentDashboardPage
