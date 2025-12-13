import { useEffect, useRef, useState, useCallback } from 'react'
import Quagga from '@ericblade/quagga2'
import { Camera, X, Flashlight, FlashlightOff, SwitchCamera } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface BarcodeScannerProps {
  onScan: (barcode: string) => void
  onClose: () => void
  className?: string
}

export function BarcodeScanner({ onScan, onClose, className }: BarcodeScannerProps) {
  const scannerRef = useRef<HTMLDivElement>(null)
  const [isInitialized, setIsInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [torch, setTorch] = useState(false)
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')
  const lastScannedRef = useRef<string | null>(null)

  const initScanner = useCallback(async () => {
    if (!scannerRef.current) return

    try {
      await Quagga.init(
        {
          inputStream: {
            type: 'LiveStream',
            target: scannerRef.current,
            constraints: {
              width: { min: 640, ideal: 1280, max: 1920 },
              height: { min: 480, ideal: 720, max: 1080 },
              facingMode: facingMode,
              aspectRatio: { min: 1, max: 2 },
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
      console.error('Scanner error:', err)
      setError('שגיאה בהפעלת הסורק')
    }
  }, [facingMode])

  useEffect(() => {
    initScanner()

    // Cleanup on unmount
    return () => {
      if (isInitialized) {
        Quagga.stop()
      }
    }
  }, [initScanner])

  useEffect(() => {
    const handleDetected = (result: any) => {
      const code = result.codeResult?.code
      if (!code) return

      // Debounce - ignore same code within 2 seconds
      if (lastScannedRef.current === code) return
      lastScannedRef.current = code

      // Vibrate if supported
      if (navigator.vibrate) {
        navigator.vibrate(100)
      }

      // Play sound feedback
      try {
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
        const oscillator = audioCtx.createOscillator()
        const gainNode = audioCtx.createGain()
        oscillator.connect(gainNode)
        gainNode.connect(audioCtx.destination)
        oscillator.frequency.value = 800
        oscillator.type = 'sine'
        gainNode.gain.value = 0.1
        oscillator.start()
        oscillator.stop(audioCtx.currentTime + 0.1)
      } catch {
        // Audio not supported
      }

      onScan(code)

      // Reset debounce after 2 seconds
      setTimeout(() => {
        lastScannedRef.current = null
      }, 2000)
    }

    Quagga.onDetected(handleDetected)

    return () => {
      Quagga.offDetected(handleDetected)
    }
  }, [onScan])

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
    Quagga.stop()
    setIsInitialized(false)
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))
  }

  useEffect(() => {
    if (!isInitialized && !error) {
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

  const handleScan = (barcode: string) => {
    setLastBarcode(barcode)
    closeScanner()
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


