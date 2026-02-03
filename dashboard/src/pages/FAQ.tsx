import { useNavigate } from 'react-router-dom'

export function FAQ() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="font-bold text-lg text-gray-900">Preguntas Frecuentes</h1>
          </div>
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-2">Como funciona el pago?</h3>
            <p className="text-gray-600 text-sm">
              Los pagos se realizan en USDC a traves del protocolo x402. El dinero se
              deposita en escrow cuando se crea la tarea y se libera automaticamente
              al completarla.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-2">Que pasa si hay una disputa?</h3>
            <p className="text-gray-600 text-sm">
              Las disputas son resueltas por un panel de arbitros. Ambas partes pueden
              presentar evidencia y el panel vota para determinar el resultado.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-2">Como construyo mi reputacion?</h3>
            <p className="text-gray-600 text-sm">
              Tu reputacion aumenta al completar tareas exitosamente. Las tareas con
              mayor valor y complejidad otorgan mas puntos de reputacion.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
