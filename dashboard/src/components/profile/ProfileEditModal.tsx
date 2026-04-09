import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { supabase } from '../../lib/supabase'
import { useProfileUpdate, type ProfileUpdateData } from '../../hooks/useProfileUpdate'
import type { Executor } from '../../types/database'
import { safeSrc } from '../../lib/safeHref'

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
  const [phone, setPhone] = useState(executor.phone || '')
  const [avatarUrl, setAvatarUrl] = useState(executor.avatar_url || '')
  const [avatarUploading, setAvatarUploading] = useState(false)
  const avatarInputRef = useRef<HTMLInputElement>(null)

  const isValid = displayName.trim().length > 0 && bio.trim().length > 0
  const modalRef = useRef<HTMLDivElement>(null)

  // Focus trap - keep focus within modal
  useEffect(() => {
    const modal = modalRef.current
    if (!modal) return

    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    // Focus first element on mount
    firstElement?.focus()

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault()
          lastElement?.focus()
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault()
          firstElement?.focus()
        }
      }
    }

    modal.addEventListener('keydown', handleTabKey)
    return () => modal.removeEventListener('keydown', handleTabKey)
  }, [])

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

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type and size
    const validTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!validTypes.includes(file.type)) return
    if (file.size > 2 * 1024 * 1024) return // 2MB max

    setAvatarUploading(true)
    try {
      const ext = file.name.split('.').pop() || 'jpg'
      const path = `avatars/${executor.id}/profile.${ext}`

      const { error: uploadError } = await supabase.storage
        .from('evidence')
        .upload(path, file, { upsert: true, contentType: file.type })

      if (uploadError) throw uploadError

      const { data: urlData } = supabase.storage
        .from('evidence')
        .getPublicUrl(path)

      setAvatarUrl(urlData.publicUrl)
    } catch (err) {
      console.error('Avatar upload failed:', err)
    } finally {
      setAvatarUploading(false)
    }
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
      phone: phone.trim() || null,
      avatar_url: avatarUrl || null,
    }

    const success = await updateProfile(data)
    if (success) {
      onSaved()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />

      {/* Modal */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="profile-edit-modal-title"
        className="relative w-full max-w-lg max-h-[90vh] mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 flex items-center justify-between">
          <div>
            <h2 id="profile-edit-modal-title" className="text-xl font-bold text-gray-900">
              {t('profile.edit.title', 'Edit Profile')}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {t('profile.edit.subtitle', 'Update your information visible to agents.')}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label={t('common.close', 'Close modal')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable form */}
        <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-5">
          {/* Avatar */}
          <div className="flex items-center gap-4">
            <div
              className="relative w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-xl font-bold cursor-pointer overflow-hidden group"
              onClick={() => avatarInputRef.current?.click()}
            >
              {avatarUrl ? (
                <img src={safeSrc(avatarUrl)} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                (displayName || 'U')[0].toUpperCase()
              )}
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              {avatarUploading && (
                <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </div>
            <div>
              <button
                type="button"
                onClick={() => avatarInputRef.current?.click()}
                disabled={avatarUploading}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                {avatarUploading ? t('common.uploading', 'Uploading...') : t('profile.edit.changePhoto', 'Change photo')}
              </button>
              <p className="text-xs text-gray-400 mt-0.5">JPG, PNG, WebP. Max 2MB.</p>
            </div>
            <input
              ref={avatarInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleAvatarUpload}
              className="hidden"
            />
          </div>

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
              {PREDEFINED_SKILLS.map((skill) => {
                const isSelected = selectedSkills.includes(skill)
                return (
                  <button
                    key={skill}
                    type="button"
                    onClick={(e) => { e.stopPropagation(); toggleSkill(skill) }}
                    className={`cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-full border transition-all ${
                      isSelected
                        ? 'bg-blue-100 border-blue-400 text-blue-800 shadow-sm'
                        : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300'
                    }`}
                  >
                    {isSelected && (
                      <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                    {skill.replace(/_/g, ' ')}
                  </button>
                )
              })}
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
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-100 border border-green-400 text-green-800 rounded-full shadow-sm"
                    >
                      <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
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
              {LANGUAGE_OPTIONS.map((lang) => {
                const isSelected = languages.includes(lang)
                return (
                  <button
                    key={lang}
                    type="button"
                    onClick={(e) => { e.stopPropagation(); toggleLanguage(lang) }}
                    className={`cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-full border transition-all ${
                      isSelected
                        ? 'bg-blue-100 border-blue-400 text-blue-800 shadow-sm'
                        : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300'
                    }`}
                  >
                    {isSelected && (
                      <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                    {lang}
                  </button>
                )
              })}
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

          {/* Phone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('profile.completion.phone', 'Phone')}{' '}
              <span className="text-gray-400 font-normal">({t('common.optional', 'optional')})</span>
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 555 123 4567"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm text-red-700">{error}</p>
                  <p className="text-xs text-red-500 mt-1">{t('common.tryAgain', 'Click Save to try again')}</p>
                </div>
              </div>
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
