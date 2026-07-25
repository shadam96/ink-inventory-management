import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Html5Qrcode } from 'html5-qrcode'
import { Camera, X, SwitchCamera, CheckCircle2, XCircle } from 'lucide-react'
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

const SCANNER_ID = 'barcode-scanner-viewport'

export function BarcodeScanner({ onScan, onClose, className }: BarcodeScannerProps) {
  const { t } = useTranslation()
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const lastScannedRef = useRef<string | null>(null)
  const processingRef = useRef(false)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const mountedRef = useRef(true)

  // Callers (PickingPage/ReceivingPage) pass fresh inline onScan/onClose
  // functions on every render. Keeping the latest callback in a ref - and
  // depending only on facingMode below - means an unrelated parent
  // re-render while the scanner is open no longer tears down and
  // restarts the camera.
  const onScanRef = useRef(onScan)
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onScanRef.current = onScan
  }, [onScan])
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  // Prepare AudioContext
  useEffect(() => {
    try {
      audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
    } catch {
      // Audio not supported
    }
    return () => {
      audioCtxRef.current?.close()
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    let scanner: Html5Qrcode | null = null

    const startScanner = async () => {
      try {
        scanner = new Html5Qrcode(SCANNER_ID, { verbose: false })
        scannerRef.current = scanner

        await scanner.start(
          { facingMode },
          {
            fps: 10,
            qrbox: { width: 280, height: 180 },
            aspectRatio: 1.0,
            disableFlip: false,
          },
          (decodedText, decodedResult) => {
            if (!mountedRef.current) return

            const code = decodedText
            const format = decodedResult?.result?.format?.formatName || 'unknown'

            // Debounce — ignore same code within 2 seconds
            if (lastScannedRef.current === code) return
            lastScannedRef.current = code

            // Don't process if already handling a scan
            if (processingRef.current) return
            processingRef.current = true

            // Vibrate
            if (navigator.vibrate) {
              navigator.vibrate(100)
            }

            // Beep
            try {
              const ctx = audioCtxRef.current
              if (ctx && ctx.state === 'running') {
                const osc = ctx.createOscillator()
                const gain = ctx.createGain()
                osc.connect(gain)
                gain.connect(ctx.destination)
                osc.frequency.value = 800
                osc.type = 'sine'
                gain.gain.value = 0.1
                osc.start()
                osc.stop(ctx.currentTime + 0.1)
              }
            } catch {
              // Audio not supported
            }

            setStatusMessage({ text: t('scanner.scanning', { code }), type: 'success' })

            Promise.resolve(onScanRef.current({ code, format }))
              .then((shouldClose) => {
                if (!mountedRef.current) return
                if (shouldClose) {
                  setStatusMessage({ text: `✓ ${code}`, type: 'success' })
                  setTimeout(() => { if (mountedRef.current) onCloseRef.current() }, 600)
                } else {
                  setStatusMessage({ text: t('scanner.notFound', { code }), type: 'error' })
                  setTimeout(() => {
                    if (mountedRef.current) setStatusMessage(null)
                    processingRef.current = false
                  }, 1500)
                }
              })
              .catch(() => {
                if (!mountedRef.current) return
                setStatusMessage({ text: t('scanner.barcodeError'), type: 'error' })
                setTimeout(() => {
                  if (mountedRef.current) setStatusMessage(null)
                  processingRef.current = false
                }, 1500)
              })

            // Reset debounce
            setTimeout(() => { lastScannedRef.current = null }, 2000)
          },
          () => {
            // QR/barcode not detected in this frame — ignore
          }
        )

        // scanner.start() resolves much slower on real mobile camera
        // hardware than on a desktop webcam, so an unmount (closing the
        // scanner, or the user backing out) frequently lands while this
        // promise is still pending. The cleanup below already ran by then
        // and saw isScanning === false, so it skipped stop() - without
        // this check the camera stream leaks and keeps running in the
        // background, blocking every future scanner.start() (including a
        // fresh instance) from acquiring the camera until the page is
        // fully reloaded.
        if (!mountedRef.current) {
          scanner.stop().catch(() => {})
        }
      } catch (err) {
        console.error('Scanner start error:', err)
        if (mountedRef.current) {
          setError(t('scanner.cameraError'))
        }
      }
    }

    startScanner()

    return () => {
      mountedRef.current = false
      if (scanner?.isScanning) {
        scanner.stop().catch(() => {})
      }
    }
    // Intentional: re-run only on facing mode change. onScan/onClose are
    // read from refs (see above) so an unmemoized callback from the
    // parent doesn't restart the camera, and adding `t` would restart it
    // on every language change too.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode])

  const switchCamera = async () => {
    try {
      if (scannerRef.current?.isScanning) {
        await scannerRef.current.stop()
      }
    } catch {
      // Already stopped
    }
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))
  }

  const retryScanner = () => {
    setError(null)
    // Trigger re-mount by toggling facingMode
    setFacingMode((prev) => prev)
  }

  return (
    <div
      className={cn(
        'fixed inset-0 z-[60] bg-black flex flex-col',
        className
      )}
    >
      {/* Header — pt includes safe area so background covers the notch */}
      <div className="flex items-center justify-between px-4 pb-3 bg-black/70 backdrop-blur-sm" style={{ paddingTop: 'max(1rem, env(safe-area-inset-top))' }}>
        <h2 className="text-white font-medium">{t('scanner.title')}</h2>
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
      <div className="flex-1 relative overflow-hidden">
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white p-4">
              <Camera className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg mb-2">{error}</p>
              <Button onClick={retryScanner}>
                {t('scanner.retry')}
              </Button>
            </div>
          </div>
        ) : (
          <div id={SCANNER_ID} className="w-full h-full" />
        )}

        {/* Status message overlay */}
        {statusMessage && (
          <div className="absolute bottom-8 inset-x-0 flex justify-center z-10">
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

      {/* Controls */}
      <div className="flex items-center justify-center gap-6 p-4 bg-black/70 backdrop-blur-sm">
        <Button
          variant="ghost"
          size="icon"
          onClick={switchCamera}
          className="text-white hover:bg-white/20 h-14 w-14 rounded-full"
          title={t('scanner.switchCamera')}
        >
          <SwitchCamera className="w-6 h-6" />
        </Button>
      </div>

      {/* Instructions */}
      <div className="text-center pb-6 safe-area-bottom text-white/60 text-sm">
        {t('scanner.instructions')}
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
