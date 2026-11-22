/**
 * Geometry-only, calibrated gaze proxy. This is NOT direct eye-contact measurement,
 * identity verification, emotion recognition or evidence of candidate dishonesty.
 * No image or face landmarks leave the browser through this module.
 */
const EYES = [
  { outer: 33, inner: 133, upper: 159, lower: 145, iris: 468 },
  { outer: 362, inner: 263, upper: 386, lower: 374, iris: 473 },
]
const between = (point, a, b) => (point - Math.min(a, b)) / Math.max(0.0001, Math.abs(b - a))
export const clamp = (n, min, max) => Math.max(min, Math.min(max, n))

/** Return null instead of manufacturing data when landmarks/irises are missing. */
/** The Face Landmarker optional 4x4 matrix contains a 3D canonical-to-face transform.
 * Values are column-major in MediaPipe Tasks. Return relative head angles in degrees.
 * If the matrix is absent, callers may still use 2D geometry as a fallback.
 */
export function measureHeadPose(matrix) {
  const a = matrix?.data
  if (!a || a.length !== 16 || !Array.from(a).every(Number.isFinite)) return null
  const zLength = Math.hypot(a[8],a[9],a[10])
  if (zLength < 0.1) return null
  const degrees = 180 / Math.PI
  return {
    yaw: Math.atan2(a[8],a[10]) * degrees,
    pitch: Math.atan2(-a[9],Math.hypot(a[8],a[10])) * degrees,
    roll: Math.atan2(a[1],a[0]) * degrees,
  }
}

export function measureGaze(landmarks, poseMatrix = null) {
  if (!Array.isArray(landmarks) || landmarks.length < 478) return null
  const eyes = []
  for (const e of EYES) {
    const [l, r, up, down, iris] = [e.outer, e.inner, e.upper, e.lower, e.iris].map(i => landmarks[i])
    if (![l, r, up, down, iris].every(p => p && Number.isFinite(p.x) && Number.isFinite(p.y))) return null
    const eyeWidth = Math.abs(l.x - r.x), eyeHeight = Math.abs(up.y - down.y)
    if (eyeWidth < 0.009 || eyeHeight < 0.0015) return null
    // Ambiguous/blinking eyes are reported as unknown; don't guess an eye direction.
    if (eyeHeight / eyeWidth < 0.11) return null
    eyes.push({ x: between(iris.x, l.x, r.x), y: between(iris.y, up.y, down.y) })
  }
  const nose = landmarks[1], left = landmarks[234], right = landmarks[454]
  if (![nose, left, right].every(Boolean)) return null
  const faceWidth = Math.abs(right.x - left.x)
  if (faceWidth < 0.05) return null
  return {
    x: (eyes[0].x + eyes[1].x) / 2,
    y: (eyes[0].y + eyes[1].y) / 2,
    head: (nose.x - (left.x + right.x) / 2) / faceWidth,
    ...(measureHeadPose(poseMatrix) || {}),
  }
}

export function averageCalibration(samples) {
  if (!Array.isArray(samples) || samples.length < 10) return null
  const good = samples.filter(s => s && [s.x, s.y, s.head].every(Number.isFinite))
  if (good.length < 10) return null
  const mean = axis => good.reduce((sum, item) => sum + item[axis], 0) / good.length
  const variance = axis => good.reduce((sum, item) => sum + (item[axis] - mean(axis)) ** 2, 0) / good.length
  // A stable neutral-position sample, not any fixed anatomical standard.
  if (variance('x') > 0.014 || variance('y') > 0.025 || variance('head') > 0.006) return null
  const result = { x: mean('x'), y: mean('y'), head: mean('head') }
  // Use pose angles only when provided by every valid sample and stable over time.
  for (const key of ['yaw','pitch','roll']) {
    if (good.every(s=>Number.isFinite(s[key]))) {
      if (variance(key) > 80) return null
      result[key] = mean(key)
    }
  }
  return result
}

export function classifyGaze(sample, baseline) {
  if (!sample || !baseline) return { kind: 'unknown', detail: 'Calibrate before checking gaze' }
  const dx = sample.x - baseline.x, dy = sample.y - baseline.y, dh = sample.head - baseline.head
  // Conservative tunable heuristics, not calibrated probability/confidence scores.
  // 3D pose matrix is preferable to a 2D nose position when it is available.
  if (['yaw','pitch','roll'].every(k=>Number.isFinite(sample[k]) && Number.isFinite(baseline[k]))) {
    if (Math.abs(sample.yaw-baseline.yaw) > 17 || Math.abs(sample.pitch-baseline.pitch) > 17 || Math.abs(sample.roll-baseline.roll) > 22)
      return {kind:'away',detail:'Approximate head direction changed from calibrated reference'}
  } else if (Math.abs(dh) > 0.15) return {kind:'away',detail:'Head turned relative to calibrated reference'}
  if (Math.abs(dx) > 0.2) return { kind: 'away', detail: 'Possible sideways eye movement (not a direct gaze measurement)' }
  if (Math.abs(dy) > 0.3) return { kind: 'away', detail: 'Possible vertical eye movement (not a direct gaze measurement)' }
  return { kind: 'center', detail: 'Eyes are near the calibrated reference direction' }
}

export function drawFaceGuides(canvas, video, faces) {
  if (!canvas || !video) return
  if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
    canvas.width = video.videoWidth; canvas.height = video.videoHeight
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  const w = canvas.width, h = canvas.height
  for (const landmarks of faces.slice(0, 2)) {
    const outline = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10]
    ctx.strokeStyle = faces.length > 1 ? 'rgba(251,140,168,.95)' : 'rgba(103,245,221,.85)'
    ctx.lineWidth = Math.max(1.7, w / 600)
    ctx.beginPath()
    for (let i = 0; i < outline.length; i++) {
      const p = landmarks[outline[i]]
      if (!p) continue
      if (i === 0) ctx.moveTo(p.x*w, p.y*h); else ctx.lineTo(p.x*w, p.y*h)
    }
    ctx.stroke()
    for (const idx of [468,473]) {
      const p = landmarks[idx]
      if (!p) continue
      ctx.fillStyle = '#f7c5ff'
      ctx.beginPath(); ctx.arc(p.x*w,p.y*h,Math.max(3,w/280),0,Math.PI*2);ctx.fill()
      ctx.strokeStyle = '#9c6af9';ctx.lineWidth = 1.5;ctx.stroke()
    }
  }
}
