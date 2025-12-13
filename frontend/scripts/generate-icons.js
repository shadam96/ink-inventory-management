import sharp from 'sharp'
import { mkdir } from 'fs/promises'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const publicDir = join(__dirname, '../public')

// SVG source for the app icon
const iconSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0ea5e9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#06b6d4;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="102" fill="url(#grad)"/>
  <g fill="white">
    <path d="M256 102 C256 102 154 230 154 307 C154 368 195 410 256 410 C317 410 358 368 358 307 C358 230 256 102 256 102 Z" />
    <circle cx="256" cy="307" r="41" fill="#0ea5e9"/>
  </g>
</svg>
`

const sizes = [
  { name: 'favicon.ico', size: 32 },
  { name: 'pwa-192x192.png', size: 192 },
  { name: 'pwa-512x512.png', size: 512 },
  { name: 'apple-touch-icon.png', size: 180 },
]

async function generateIcons() {
  console.log('Generating PWA icons...')
  
  try {
    await mkdir(publicDir, { recursive: true })
    
    const svgBuffer = Buffer.from(iconSvg)
    
    for (const { name, size } of sizes) {
      const outputPath = join(publicDir, name)
      
      if (name.endsWith('.ico')) {
        // For favicon, create PNG first then rename
        await sharp(svgBuffer)
          .resize(size, size)
          .png()
          .toFile(outputPath.replace('.ico', '.png'))
        console.log(`Generated: ${name} (as png)`)
      } else {
        await sharp(svgBuffer)
          .resize(size, size)
          .png()
          .toFile(outputPath)
        console.log(`Generated: ${name}`)
      }
    }
    
    console.log('All icons generated successfully!')
  } catch (error) {
    console.error('Error generating icons:', error)
    process.exit(1)
  }
}

generateIcons()

