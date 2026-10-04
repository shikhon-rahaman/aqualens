/** Resize an image file to max long edge and re-encode as JPEG (strips EXIF). */

const MAX_EDGE = 1024
const JPEG_QUALITY = 0.85

function loadImage(file: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Could not read that image. Try another photo.'))
    }
    img.src = url
  })
}

export async function resizeImageToJpeg(
  file: Blob,
  maxEdge: number = MAX_EDGE,
): Promise<Blob> {
  const img = await loadImage(file)
  const longEdge = Math.max(img.width, img.height)
  const scale = longEdge > maxEdge ? maxEdge / longEdge : 1
  const width = Math.max(1, Math.round(img.width * scale))
  const height = Math.max(1, Math.round(img.height * scale))

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Canvas is not available in this browser.')
  }
  ctx.drawImage(img, 0, 0, width, height)

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob((b) => resolve(b), 'image/jpeg', JPEG_QUALITY)
  })
  if (!blob) {
    throw new Error('Could not encode the photo as JPEG.')
  }
  return blob
}
