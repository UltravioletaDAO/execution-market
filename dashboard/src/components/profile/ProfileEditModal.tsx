import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useProfileUpdate, type ProfileUpdateData } from '../../hooks/useProfileUpdate'
import type { Executor } from '../../types/database'

const PREDEFINED_SKILLS = [
  'photography',
  'delivery',
  'verification',
  'data_collection',
  'translation',
  'notarization',
  'physical_inspection',
  'document_handling',
]

const LANGUAGE_OPTIONS = [
  'Spanish',
  'English',
  'Portuguese',
  'French',
  'German',
  'Italian',
  'Chinese',
  'Japanese',
]

interface ProfileEditModalProps {
  executor: Executor
  onClose: () => void
  onSaved: () => void
}

export function ProfileEditModal({ executor, onClose, onSaved }: ProfileEditModalProps) {
  const { t } = useTranslation()
  const { updateProfile, saving, error } = useProfileUpdate()

  const [displayName, setDisplayName] = useState(executor.display_name || '')
  const [bio, setBio] = useState(executor.bio || '')
  const [selectedSkills, setSelectedSkills] = useState<string[]>(executor.skills || [])
  const [customSkill, setCustomSkill] = useState('')
  const [languages, setLanguages] = useState<string[]>(executor.languages?.length ? executor.languages : ['Spanish'])
  const [locationCity, setLocationCity] = useState(executor.location_city || '')
  const [locationCountry, setLocationCountry] = useState(executor.location_country || '')
  const [email, setEmail] = useState(executor.email || '')

  const isValid = displayName.trim().length > 0 && bio.trim().length > 0

  // Close on escape
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose])

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    )
  }

  const addCustomSkill = () => {
    const trimmed = customSkill.trim().toLowerCase()
    if (trimmed && !selectedSkills.includes(trimmed)) {
      setSelectedSkills((prev) => [...prev, trimmed])
      setCustomSkill('')
    }
  }

  const toggleLanguage = (lang: string) => {
    setLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    )
  }

  const handleSubmit = async () => {
    if (!isValid) return

    const data: ProfileUpdateData = {
      display_name: displayName.trim(),
      bio: bio.trim(),
      skills: selectedSkills,
      languages,
      location_city: locationCity.trim(),
      location_country: locationCountry.trim(),
      email: email.trim() || null,
    }

    const success = await updateProfile(data)
    if (success) {
      onSaved()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-lg max-h-[90vh] mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              {t('profile.edit.title', 'Edit Profile')}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {t('profile.edit.subtitle', 'Update your information visible to agents.')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable form */}
        <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-5">
          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.completion.displayName', 'Display Name')} *
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              maxLength={50}
            />
          </div>

          {/* Bio */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.completion.bio', 'About You')} *
            </label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
              rows={3}
              maxLength={500}
            />
            <div className="text-xs text-gray-400 mt-1 text-right">{bio.length}/500</div>
          </div>

          {/* Skills */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('profile.completion.skills', 'Skills')}
            </label>
            <div className="flex flex-wrap gap-2">
              {PREDEFINED_SKILLS.map((skill) => (
                <button
                  key={skill}
                  type="button"
                  onClick={() => toggleSkill(skill)}
                  className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                    selectedSkills.includes(skill)
                      ? 'bg-blue-50 border-blue-300 text-blue-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {skill.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
            <div className="flex gap-2 mt-2">
              <input
                type="text"
                value={customSkill}
                onChange={(e) => setCustomSkill(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomSkill())}
                placeholder={t('skills.customPlaceholder', 'Type your skill...')}
                className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
              <button
                type="button"
                onClick={addCustomSkill}
                disabled={!customSkill.trim()}
                className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-40 transition-colors"
              >
                {t('common.add', 'Add')}
              </button>
            </div>
            {selectedSkills.filter((s) => !PREDEFINED_SKILLS.includes(s)).length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {selectedSkills
                  .filter((s) => !PREDEFINED_SKILLS.includes(s))
                  .map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-green-50 border border-green-200 text-green-700 rounded-full"
                    >
                      {skill}
                      <button
                        type="button"
                        onClick={() => toggleSkill(skill)}
                        className="ml-0.5 text-green-500 hover:text-green-700"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
              </div>
            )}
          </div>

          {/* Languages */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('profile.completion.languages', 'Languages')}
            </label>
            <div className="flex flex-wrap gap-2">
              {LANGUAGE_OPTIONS.map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => toggleLanguage(lang)}
                  className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                    languages.includes(lang)
                      ? 'bg-blue-50 border-blue-300 text-blue-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>

          {/* Location */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('profile.completion.city', 'City')}
              </label>
              <input
                type="text"
                value={locationCity}
                onChange={(e) => setLocationCity(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('profile.completion.country', 'Country')}
              </label>
              <input
                type="text"
                value={locationCountry}
                onChange={(e) => setLocationCountry(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.completion.email', 'Email')}{' '}
              <span className="text-gray-400 font-normal">({t('common.optional', 'optional')})</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || saving}
            className="flex-1 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
          </button>
        </div>
      </div>
    </div>
  )
}
