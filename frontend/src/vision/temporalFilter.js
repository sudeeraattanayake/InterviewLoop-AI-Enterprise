/** Small per-session median filter to remove single-frame landmark jumps.
 * This is NOT a confidence score or proof of eye contact.
 */
export class TemporalGazeFilter {
  constructor(windowSize = 5) { this.windowSize = windowSize; this.values = [] }
  reset() { this.values = [] }
  push(sample) {
    if (!sample) return null
    this.values.push(sample)
    if (this.values.length > this.windowSize) this.values.shift()
    const median = key => {
      const values = this.values.map(x => x[key]).filter(Number.isFinite).sort((a,b)=>a-b)
      if (!values.length) return undefined
      const n = values.length
      return n % 2 ? values[(n-1)/2] : (values[n/2-1] + values[n/2])/2
    }
    return Object.fromEntries(['x','y','head','yaw','pitch','roll'].map(key=>[key,median(key)]).filter(([,value])=>value!==undefined))
  }
}
