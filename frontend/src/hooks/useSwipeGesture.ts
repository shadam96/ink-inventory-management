import { useRef, useCallback, useEffect } from 'react'

type SwipeDirection = 'left' | 'right' | 'up' | 'down'

interface UseSwipeGestureOptions {
  onSwipe?: (direction: SwipeDirection) => void
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  onSwipeUp?: () => void
  onSwipeDown?: () => void
  threshold?: number
  disabled?: boolean
}

export function useSwipeGesture({
  onSwipe,
  onSwipeLeft,
  onSwipeRight,
  onSwipeUp,
  onSwipeDown,
  threshold = 50,
  disabled = false,
}: UseSwipeGestureOptions) {
  const containerRef = useRef<HTMLDivElement>(null)
  const startX = useRef(0)
  const startY = useRef(0)
  const startTime = useRef(0)

  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      if (disabled) return

      startX.current = e.touches[0].clientX
      startY.current = e.touches[0].clientY
      startTime.current = Date.now()
    },
    [disabled]
  )

  const handleTouchEnd = useCallback(
    (e: TouchEvent) => {
      if (disabled) return

      const endX = e.changedTouches[0].clientX
      const endY = e.changedTouches[0].clientY
      const endTime = Date.now()

      const diffX = endX - startX.current
      const diffY = endY - startY.current
      const duration = endTime - startTime.current

      // Ignore if swipe took too long (>500ms)
      if (duration > 500) return

      const absX = Math.abs(diffX)
      const absY = Math.abs(diffY)

      // Determine if horizontal or vertical swipe
      if (absX > absY && absX > threshold) {
        // Horizontal swipe
        const direction: SwipeDirection = diffX > 0 ? 'right' : 'left'
        onSwipe?.(direction)
        if (direction === 'left') onSwipeLeft?.()
        if (direction === 'right') onSwipeRight?.()
      } else if (absY > absX && absY > threshold) {
        // Vertical swipe
        const direction: SwipeDirection = diffY > 0 ? 'down' : 'up'
        onSwipe?.(direction)
        if (direction === 'up') onSwipeUp?.()
        if (direction === 'down') onSwipeDown?.()
      }
    },
    [disabled, threshold, onSwipe, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown]
  )

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    container.addEventListener('touchstart', handleTouchStart)
    container.addEventListener('touchend', handleTouchEnd)

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [handleTouchStart, handleTouchEnd])

  return { containerRef }
}

