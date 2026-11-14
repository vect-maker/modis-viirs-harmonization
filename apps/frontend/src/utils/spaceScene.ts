export interface SpaceStar {
  x: number
  y: number
  radius: number
  opacity: number
  phase: number
  speed: number
  color: string
  bright: boolean
}

export interface SpaceMeteor {
  start: number
  duration: number
  x: number
  y: number
  distance: number
  angle: number
}

export function createSpaceStars(width: number, height: number): SpaceStar[] {
  let seed = 7391
  const random = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0
    return seed / 4294967296
  }
  const count = Math.min(650, Math.max(100, Math.round((width * height) / 3600)))
  return Array.from({ length: count }, (_, index) => {
    const bright = index % 47 === 0
    const tint = random()
    return {
      x: random(),
      y: random(),
      radius: bright ? 1.4 + random() * 0.5 : 0.35 + random() * 0.8,
      opacity: 0.25 + random() * 0.6,
      phase: random() * Math.PI * 2,
      speed: 0.4 + random() * 0.6,
      color: tint < 0.15 ? '176, 205, 255' : tint > 0.92 ? '255, 219, 180' : '226, 234, 245',
      bright,
    }
  })
}

export function paintSpaceDust(ctx: CanvasRenderingContext2D, width: number, height: number) {
  ctx.fillStyle = '#020409'
  ctx.fillRect(0, 0, width, height)
  // Distant, understated color keeps the map and its red detections in focus.
  const glow = ctx.createRadialGradient(
    width * 0.2,
    height * 0.3,
    0,
    width * 0.2,
    height * 0.3,
    width * 0.7,
  )
  glow.addColorStop(0, '#10223d26')
  glow.addColorStop(1, '#02040900')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, width, height)
  for (let index = 0; index < 7; index++) {
    ctx.save()
    ctx.translate(((index * 0.381 + 0.14) % 1) * width, ((index * 0.618 + 0.19) % 1) * height)
    ctx.rotate(index * 1.2)
    ctx.scale(2.2, 0.7)
    const galaxy = ctx.createRadialGradient(0, 0, 0, 0, 0, 5)
    galaxy.addColorStop(0, 'rgba(238, 213, 190, 0.28)')
    galaxy.addColorStop(0.35, 'rgba(197, 201, 224, 0.1)')
    galaxy.addColorStop(1, 'rgba(197, 201, 224, 0)')
    ctx.fillStyle = galaxy
    ctx.fillRect(-5, -5, 10, 10)
    ctx.restore()
  }
}

export function paintSpaceStars(
  ctx: CanvasRenderingContext2D,
  stars: SpaceStar[],
  width: number,
  height: number,
  time: number,
) {
  for (const star of stars) {
    const x = star.x * width
    const y = star.y * height
    const twinkle = 0.7 + 0.3 * Math.sin(time * star.speed + star.phase)
    const alpha = star.opacity * twinkle
    if (star.bright) {
      const glow = ctx.createRadialGradient(x, y, 0, x, y, 11)
      glow.addColorStop(0, 'rgba(' + star.color + ', ' + alpha * 0.3 + ')')
      glow.addColorStop(1, 'rgba(' + star.color + ', 0)')
      ctx.fillStyle = glow
      ctx.fillRect(x - 11, y - 11, 22, 22)
      ctx.strokeStyle = 'rgba(' + star.color + ', ' + alpha * 0.5 + ')'
      ctx.lineWidth = 0.5
      ctx.beginPath()
      ctx.moveTo(x - 5, y)
      ctx.lineTo(x + 5, y)
      ctx.moveTo(x, y - 5)
      ctx.lineTo(x, y + 5)
      ctx.stroke()
    }
    ctx.fillStyle = 'rgba(' + star.color + ', ' + alpha + ')'
    ctx.beginPath()
    ctx.arc(x, y, star.radius, 0, Math.PI * 2)
    ctx.fill()
  }
}

export function paintSpaceMeteor(
  ctx: CanvasRenderingContext2D,
  meteor: SpaceMeteor,
  width: number,
  height: number,
  time: number,
) {
  const progress = (time - meteor.start) / meteor.duration
  if (progress < 0 || progress >= 1) return
  const x = meteor.x * width + Math.cos(meteor.angle) * meteor.distance * progress
  const y = meteor.y * height + Math.sin(meteor.angle) * meteor.distance * progress
  const length = Math.min(170, width * 0.15)
  ctx.save()
  ctx.globalAlpha = Math.sin(progress * Math.PI) * 0.8
  ctx.translate(x, y)
  ctx.rotate(meteor.angle)
  const trail = ctx.createLinearGradient(-length, 0, 0, 0)
  trail.addColorStop(0, 'rgba(151, 187, 232, 0)')
  trail.addColorStop(0.75, 'rgba(196, 218, 251, 0.45)')
  trail.addColorStop(1, 'rgba(246, 249, 255, 1)')
  ctx.fillStyle = trail
  ctx.beginPath()
  ctx.moveTo(-length, 0)
  ctx.lineTo(0, -1.2)
  ctx.lineTo(0, 1.2)
  ctx.closePath()
  ctx.fill()
  ctx.fillStyle = '#f3f7ff'
  ctx.shadowColor = '#b1d2ff'
  ctx.shadowBlur = 8
  ctx.beginPath()
  ctx.arc(0, 0, 1.6, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
}
