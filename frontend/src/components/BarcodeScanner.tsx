import { useEffect, useRef, useState, useCallback } from 'react'
import Quagga from '@ericblade/quagga2'
import { Camera, X, Flashlight, FlashlightOff, SwitchCamera, CheckCircle2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface ScanResult {
  code: string
  format: string
}

interface BarcodeScannerProps {
  /** Called on every valid detection. Return true to close the scanner, false to keep scanning. */
  onScan: (result: ScanResult) => Promise<boolean> | boolean
  onClose: () => void
  className?: string
}

const MIN_CONFIDENCE = 0.6

export function BarcodeScanner({ onScan, onClose, className }: BarcodeScannerProps) {
  const scannerRef = useRef<HTMLDivElement>(null)
  const [isInitialized, setIsInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [torch, setTorch] = useState(false)
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const lastScannedRef = useRef<string | null>(null)
  const initializingRef = useRef(false)
  const processingRef = useRef(false)
  const audioCtxRef = useRef<AudioContext | null>(null)

  const stopScanner = useCallback(() => {
    try {
      Quagga.stop()
    } catch {
      // Already stopped
    }
    setIsInitialized(false)
  }, [])

  const initScanner = useCallback(async () => {
    if (!scannerRef.current || initializingRef.current) return
    initializingRef.current = true

    try {
      await Quagga.init(
        {
          inputStream: {
            type: 'LiveStream',
            target: scannerRef.current,
            constraints: {
              facingMode: facingMode,
              width: { ideal: 1280 },
              height: { ideal: 720 },
            },
          },
          locator: {
            patchSize: 'medium',
            halfSample: true,
          },
          numOfWorkers: navigator.hardwareConcurrency || 4,
          frequency: 10,
          decoder: {
            readers: [
              'ean_reader',
              'ean_8_reader',
              'code_128_reader',
              'code_39_reader',
              'upc_reader',
              'upc_e_reader',
              'codabar_reader',
              'i2of5_reader',
            ],
          },
          locate: true,
        },
        (err) => {
          initializingRef.current = false
          if (err) {
            console.error('Quagga init error:', err)
            setError('לא ניתן לגשת למצלמה. אנא אשר הרשאות מצלמה.')
            return
          }
          Quagga.start()
          setIsInitialized(true)
        }
      )
    } catch (err) {
      initializingRef.current = false
      console.error('Scanner error:', err)
      setError('שגיאה בהפעלת הסורק')
    }
  }, [facingMode])

  // Init on mount, cleanup on unmount
  useEffect(() => {
    initScanner()

    return () => {
      stopScanner()
      audioCtxRef.current?.close()
    }
  }, [initScanner, stopScanner])

  // Prepare AudioContext on component mount (within user gesture context)
  useEffect(() => {
    try {
      audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
    } catch {
      // Audio not supported
    }
  }, [])

  useEffect(() => {
    const handleDetected = async (result: any) => {
      const code = result.codeResult?.code
      const format = result.codeResult?.format
      if (!code) return

      // Check confidence — reject low-confidence reads
      const errors = result.codeResult?.decodedCodes
        ?.filter((d: any) => typeof d.error === 'number')
        ?.map((d: any) => d.error) || []
      if (errors.length > 0) {
        const avgError = errors.reduce((s: number, e: number) => s + e, 0) / errors.length
        if (avgError > (1 - MIN_CONFIDENCE)) return
      }

      // Debounce — ignore same code within 2 seconds
      if (lastScannedRef.current === code) return
      lastScannedRef.current = code

      // Don't process if already handling a scan
      if (processingRef.current) return
      processingRef.current = true

      // Vibrate if supported
      if (navigator.vibrate) {
        navigator.vibrate(100)
      }

      // Play sound feedback
      try {
        const ctx = audioCtxRef.current
        if (ctx && ctx.state === 'running') {
          const oscillator = ctx.createOscillator()
          const gainNode = ctx.createGain()
          oscillator.connect(gainNode)
          gainNode.connect(ctx.destination)
          oscillator.frequency.value = 800
          oscillator.type = 'sine'
          gainNode.gain.value = 0.1
          oscillator.start()
          oscillator.stop(ctx.currentTime + 0.1)
        }
      } catch {
        // Audio not supported
      }

      try {
        const shouldClose = await onScan({ code, format })
        if (shouldClose) {
          // Success — brief green flash then close
          setStatusMessage({ text: `✓ ${code}`, type: 'success' })
          setTimeout(() => onClose(), 600)
        } else {
          // Not found — show message, keep scanning
          setStatusMessage({ text: `${code} — לא נמצא`, type: 'error' })
          setTimeout(() => {
            setStatusMessage(null)
            processingRef.current = false
          }, 1500)
        }
      } catch {
        setStatusMessage({ text: 'שגיאה בבדיקת ברקוד', type: 'error' })
        setTimeout(() => {
          setStatusMessage(null)
          processingRef.current = false
        }, 1500)
      }

      // Reset debounce after 2 seconds
      setTimeout(() => {
        lastScannedRef.current = null
      }, 2000)
    }

    Quagga.onDetected(handleDetected)

    return () => {
      Quagga.offDetected(handleDetected)
    }
  }, [onScan, onClose])

  const toggleTorch = async () => {
    try {
      const track = Quagga.CameraAccess.getActiveTrack()
      if (track && 'applyConstraints' in track) {
        await track.applyConstraints({
          advanced: [{ torch: !torch } as any],
        })
        setTorch(!torch)
      }
    } catch {
      // Torch not supported
    }
  }

  const switchCamera = () => {
    stopScanner()
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))
  }

  // Re-init when facingMode changes (after switchCamera)
  useEffect(() => {
    if (!isInitialized && !error && !initializingRef.current) {
      initScanner()
    }
  }, [facingMode, isInitialized, error, initScanner])

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 bg-black flex flex-col',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-black/50">
        <h2 className="text-white font-medium">סריקת ברקוד</h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="text-white hover:bg-white/20"
        >
          <X className="w-6 h-6" />
        </Button>
      </div>

      {/* Scanner viewport */}
      <div className="flex-1 relative">
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white p-4">
              <Camera className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg mb-2">{error}</p>
              <Button onClick={() => {
                setError(null)
                initializingRef.current = false
                initScanner()
              }}>
                נסה שוב
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div
              ref={scannerRef}
              className="w-full h-full"
              style={{
                position: 'relative',
              }}
            />

            {/* Scan overlay */}
            <div className="absolute inset-0 pointer-events-none">
              {/* Darkened corners */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-72 h-48 relative">
                  {/* Corner markers */}
                  <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-primary rounded-tl-lg" />
                  <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-primary rounded-tr-lg" />
                  <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-primary rounded-bl-lg" />
                  <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-primary rounded-br-lg" />

                  {/* Scan line animation */}
                  <div className="absolute left-4 right-4 top-1/2 h-0.5 bg-primary/50 animate-pulse" />
                </div>
              </div>

              {/* Status message overlay */}
              {statusMessage && (
                <div className="absolute bottom-24 left-0 right-0 flex justify-center">
                  <div className={cn(
                    'flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium shadow-lg',
                    statusMessage.type === 'success'
                      ? 'bg-green-600 text-white'
                      : 'bg-red-600 text-white'
                  )}>
                    {statusMessage.type === 'success' ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                    <span dir="ltr">{statusMessage.text}</span>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-6 p-6 bg-black/50">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTorch}
          className="text-white hover:bg-white/20 h-14 w-14 rounded-full"
          title="פנס"
        >
          {torch ? (
            <FlashlightOff className="w-6 h-6" />
          ) : (
            <Flashlight className="w-6 h-6" />
          )}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={switchCamera}
          className="text-white hover:bg-white/20 h-14 w-14 rounded-full"
          title="החלף מצלמה"
        >
          <SwitchCamera className="w-6 h-6" />
        </Button>
      </div>

      {/* Instructions */}
      <div className="text-center pb-6 text-white/70 text-sm">
        מקם את הברקוד בתוך המסגרת
      </div>
    </div>
  )
}

// Hook for easy scanner usage
export function useBarcodeScanner() {
  const [isOpen, setIsOpen] = useState(false)
  const [lastBarcode, setLastBarcode] = useState<string | null>(null)

  const openScanner = () => setIsOpen(true)
  const closeScanner = () => setIsOpen(false)

  const handleScan = (result: ScanResult) => {
    setLastBarcode(result.code)
    closeScanner()
    return true
  }

  return {
    isOpen,
    openScanner,
    closeScanner,
    lastBarcode,
    handleScan,
    ScannerComponent: isOpen ? (
      <BarcodeScanner onScan={handleScan} onClose={closeScanner} />
    ) : null,
  }
}
