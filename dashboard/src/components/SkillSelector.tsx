/**
 * SkillSelector - Skill selection for executor profiles
 *
 * Features:
 * - Predefined skill categories
 * - Search/filter skills
 * - Multi-select with chips
 * - Skill verification status
 * - Custom skill input
 */

import { useState, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'

// Types
interface Skill {
  id: string
  name: string
  category: string
  verified?: boolean
}

interface SkillSelectorProps {
  selectedSkills: string[]
  onSkillsChange: (skills: string[]) => void
  verifiedSkills?: string[]
  maxSkills?: number
  showCategories?: boolean
}

// Predefined skills by category
const SKILL_CATEGORIES: { id: string; name: string; skills: Omit<Skill, 'category'>[] }[] = [
  {
    id: 'verification',
    name: 'Verification',
    skills: [
      { id: 'photo_verification', name: 'Photo verification' },
      { id: 'location_verification', name: 'Location verification' },
      { id: 'document_verification', name: 'Document verification' },
      { id: 'price_verification', name: 'Price verification' },
      { id: 'inventory_check', name: 'Inventory check' },
    ],
  },
  {
    id: 'data_collection',
    name: 'Data Collection',
    skills: [
      { id: 'survey_completion', name: 'Survey completion' },
      { id: 'data_entry', name: 'Data entry' },
      { id: 'form_filling', name: 'Form filling' },
      { id: 'research', name: 'Research' },
      { id: 'lead_generation', name: 'Lead generation' },
    ],
  },
  {
    id: 'content',
    name: 'Content',
    skills: [
      { id: 'photography', name: 'Photography' },
      { id: 'video_recording', name: 'Video recording' },
      { id: 'audio_recording', name: 'Audio recording' },
      { id: 'writing', name: 'Writing' },
      { id: 'social_media', name: 'Social media' },
    ],
  },
  {
    id: 'language',
    name: 'Languages',
    skills: [
      { id: 'spanish_native', name: 'Native Spanish' },
      { id: 'english_fluent', name: 'Fluent English' },
      { id: 'portuguese', name: 'Portuguese' },
      { id: 'french', name: 'French' },
      { id: 'translation', name: 'Translation' },
      { id: 'transcription', name: 'Transcription' },
    ],
  },
  {
    id: 'physical',
    name: 'Physical Tasks',
    skills: [
      { id: 'delivery', name: 'Deliveries' },
      { id: 'driving', name: 'Driving' },
      { id: 'walking', name: 'Walking' },
      { id: 'lifting', name: 'Heavy lifting' },
      { id: 'assembly', name: 'Assembly' },
    ],
  },
  {
    id: 'digital',
    name: 'Digital',
    skills: [
      { id: 'smartphone_proficient', name: 'Smartphone proficient' },
      { id: 'computer_proficient', name: 'Computer proficient' },
      { id: 'app_testing', name: 'App testing' },
      { id: 'web_testing', name: 'Web testing' },
      { id: 'ai_training', name: 'AI training' },
    ],
  },
  {
    id: 'specialized',
    name: 'Specialized',
    skills: [
      { id: 'mystery_shopping', name: 'Mystery shopping' },
      { id: 'quality_control', name: 'Quality control' },
      { id: 'customer_service', name: 'Customer service' },
      { id: 'sales', name: 'Sales' },
      { id: 'teaching', name: 'Teaching' },
    ],
  },
]

// Flatten all skills for search
const ALL_SKILLS: Skill[] = SKILL_CATEGORIES.flatMap((cat) =>
  cat.skills.map((skill) => ({ ...skill, category: cat.id }))
)

export function SkillSelector({
  selectedSkills,
  onSkillsChange,
  verifiedSkills = [],
  maxSkills = 20,
  showCategories = true,
}: SkillSelectorProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [showCustomInput, setShowCustomInput] = useState(false)
  const [customSkill, setCustomSkill] = useState('')

  // Filter skills by search
  const filteredSkills = useMemo(() => {
    if (!searchQuery) return ALL_SKILLS
    const query = searchQuery.toLowerCase()
    return ALL_SKILLS.filter((skill) =>
      skill.name.toLowerCase().includes(query) ||
      skill.id.toLowerCase().includes(query)
    )
  }, [searchQuery])

  // Group filtered skills by category
  const groupedSkills = useMemo(() => {
    const groups: Record<string, Skill[]> = {}
    filteredSkills.forEach((skill) => {
      if (!groups[skill.category]) {
        groups[skill.category] = []
      }
      groups[skill.category].push(skill)
    })
    return groups
  }, [filteredSkills])

  // Toggle skill selection
  const toggleSkill = useCallback((skillId: string) => {
    if (selectedSkills.includes(skillId)) {
      onSkillsChange(selectedSkills.filter((id) => id !== skillId))
    } else if (selectedSkills.length < maxSkills) {
      onSkillsChange([...selectedSkills, skillId])
    }
  }, [selectedSkills, onSkillsChange, maxSkills])

  // Add custom skill
  const addCustomSkill = useCallback(() => {
    if (!customSkill.trim()) return

    const skillId = customSkill.toLowerCase().replace(/\s+/g, '_')
    if (!selectedSkills.includes(skillId)) {
      onSkillsChange([...selectedSkills, skillId])
    }
    setCustomSkill('')
    setShowCustomInput(false)
  }, [customSkill, selectedSkills, onSkillsChange])

  // Get skill display name
  const getSkillName = useCallback((skillId: string) => {
    const skill = ALL_SKILLS.find((s) => s.id === skillId)
    return skill?.name || skillId.replace(/_/g, ' ')
  }, [])

  // Check if skill is verified
  const isVerified = useCallback((skillId: string) => {
    return verifiedSkills.includes(skillId)
  }, [verifiedSkills])

  return (
    <div className="space-y-4">
      {/* Selected skills */}
      {selectedSkills.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedSkills.map((skillId) => (
            <span
              key={skillId}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
                isVerified(skillId)
                  ? 'bg-green-100 text-green-800'
                  : 'bg-blue-100 text-blue-800'
              }`}
            >
              {isVerified(skillId) && (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              )}
              <span>{getSkillName(skillId)}</span>
              <button
                onClick={() => toggleSkill(skillId)}
                className="ml-1 hover:text-red-600"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Counter */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {selectedSkills.length} / {maxSkills} {t('skills.selected', 'skills selected')}
        </span>
        {selectedSkills.length >= maxSkills && (
          <span className="text-sm text-yellow-600">
            {t('skills.maxReached', 'Maximum reached')}
          </span>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('skills.search', 'Search skills...')}
          className="w-full pl-10 pr-4 py-2.5 bg-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
        />
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>

      {/* Skill categories */}
      {showCategories && (
        <div className="space-y-2">
          {SKILL_CATEGORIES.map((category) => {
            const categorySkills = groupedSkills[category.id] || []
            if (categorySkills.length === 0 && searchQuery) return null

            const isExpanded = expandedCategory === category.id || !!searchQuery
            const selectedCount = categorySkills.filter((s) =>
              selectedSkills.includes(s.id)
            ).length

            return (
              <div key={category.id} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedCategory(isExpanded && !searchQuery ? null : category.id)}
                  className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">
                      {t(`skillCategories.${category.id}`, category.name)}
                    </span>
                    {selectedCount > 0 && (
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full">
                        {selectedCount}
                      </span>
                    )}
                  </div>
                  <svg
                    className={`w-5 h-5 text-gray-400 transition-transform ${
                      isExpanded ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {isExpanded && (
                  <div className="p-3 bg-white">
                    <div className="flex flex-wrap gap-2">
                      {(searchQuery ? categorySkills : category.skills.map((s) => ({ ...s, category: category.id }))).map((skill) => {
                        const isSelected = selectedSkills.includes(skill.id)
                        const verified = isVerified(skill.id)

                        return (
                          <button
                            key={skill.id}
                            onClick={() => toggleSkill(skill.id)}
                            disabled={!isSelected && selectedSkills.length >= maxSkills}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors ${
                              isSelected
                                ? verified
                                  ? 'bg-green-600 text-white'
                                  : 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed'
                            }`}
                          >
                            {isSelected && (
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                            {verified && !isSelected && (
                              <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                            )}
                            <span>{t(`skills.${skill.id}`, skill.name)}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Custom skill input */}
      <div className="border-t border-gray-200 pt-4">
        {showCustomInput ? (
          <div className="flex gap-2">
            <input
              type="text"
              value={customSkill}
              onChange={(e) => setCustomSkill(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addCustomSkill()}
              placeholder={t('skills.customPlaceholder', 'Type your skill...')}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <button
              onClick={addCustomSkill}
              disabled={!customSkill.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('common.add', 'Add')}
            </button>
            <button
              onClick={() => setShowCustomInput(false)}
              className="px-4 py-2 text-gray-600 text-sm hover:text-gray-800"
            >
              {t('common.cancel', 'Cancel')}
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowCustomInput(true)}
            disabled={selectedSkills.length >= maxSkills}
            className="flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {t('skills.addCustom', 'Add custom skill')}
          </button>
        )}
      </div>

      {/* Info about verification */}
      <div className="flex items-start gap-2 p-3 bg-gray-50 rounded-lg">
        <svg className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-sm text-gray-600">
          {t('skills.verificationInfo', 'Verified skills increase your visibility and trust. You can verify skills by completing related tasks.')}
        </p>
      </div>
    </div>
  )
}

export type { Skill }
export default SkillSelector
