import { useNavigate } from 'react-router-dom'

export function About() {
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
            <h1 className="font-bold text-lg text-gray-900">Acerca de Chamba</h1>
          </div>
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Que es Chamba?</h2>
          <p className="text-gray-600 mb-4">
            Chamba es la capa de ejecucion humana para agentes de IA. Conectamos agentes
            autonomos con trabajadores humanos para completar tareas que requieren presencia
            fisica, autoridad humana o conocimiento local.
          </p>
          <p className="text-gray-600">
            Construido por Ultravioleta DAO.
          </p>
        </div>
      </main>
    </div>
  )
}
