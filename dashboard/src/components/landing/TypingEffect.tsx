import { useState, useEffect, useCallback } from 'react'

interface TypingEffectProps {
  phrases: string[]
  typeSpeed?: number
  deleteSpeed?: number
  pauseDuration?: number
}

export function TypingEffect({
  phrases,
  typeSpeed = 50,
  deleteSpeed = 30,
  pauseDuration = 2000,
}: TypingEffectProps) {
  const [text, setText] = useState('')
  const [phraseIndex, setPhraseIndex] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)

  const tick = useCallback(() => {
    const currentPhrase = phrases[phraseIndex]

    if (isDeleting) {
      setText(currentPhrase.substring(0, text.length - 1))
    } else {
      setText(currentPhrase.substring(0, text.length + 1))
    }
  }, [text, phraseIndex, isDeleting, phrases])

  useEffect(() => {
    const currentPhrase = phrases[phraseIndex]

    if (!isDeleting && text === currentPhrase) {
      const timeout = setTimeout(() => setIsDeleting(true), pauseDuration)
      return () => clearTimeout(timeout)
    }

    if (isDeleting && text === '') {
      setIsDeleting(false)
      setPhraseIndex((prev) => (prev + 1) % phrases.length)
      return
    }

    const speed = isDeleting ? deleteSpeed : typeSpeed
    const timeout = setTimeout(tick, speed)
    return () => clearTimeout(timeout)
  }, [text, isDeleting, phraseIndex, phrases, typeSpeed, deleteSpeed, pauseDuration, tick])

  return (
    <span className="inline-flex items-baseline">
      <span>{text}</span>
      <span className="ml-0.5 inline-block w-0.5 h-6 bg-amber-500 animate-blink" />
    </span>
  )
}
