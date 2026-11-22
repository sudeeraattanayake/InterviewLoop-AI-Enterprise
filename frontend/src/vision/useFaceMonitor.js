import {useCallback,useEffect,useRef,useState} from 'react'
import {averageCalibration,classifyGaze,drawFaceGuides,measureGaze} from './gazeMath'
import {TemporalGazeFilter} from './temporalFilter'

const INITIAL = {kind:'off', label:'Vision monitoring off', detail:'Camera guidance starts automatically after separate consent', faceCount:0}
const labelFor = {
  off:'Vision monitoring off', loading:'Initializing vision model', ready:'Waiting for stable calibration',
  calibrating:'Calibrating eye direction', center:'Near camera reference',
  away:'Possible look away', no_face:'Face not visible', multiple:'Multiple faces visible',
  unknown:'Eyes unclear / blinking', error:'Vision model unavailable',
}
const sustainedMs = {away:3000, no_face:2700, multiple:1800}

/**
 * Runs ONLY in candidate browser. No landmark, image, identity or gaze stream is sent
 * to API; event history is ephemeral and disappears when the studio unmounts.
 */
export function useFaceMonitor({enabled,videoRef,canvasRef,stream}) {
  const [status,setStatus] = useState(INITIAL)
  const [events,setEvents] = useState([])
  const [baseline,setBaseline] = useState(null)
  const [calibrating,setCalibrating] = useState(false)
  const baselineRef = useRef(null), calibrateRef = useRef(false)
  const samplesRef = useRef([]), lastUpdateRef = useRef(0), streakRef = useRef({kind:'',since:0,reported:false}), smoothRef = useRef(new TemporalGazeFilter(5)), lastCalibFrameRef=useRef(0)
  const beginCalibration = useCallback(()=>{
    samplesRef.current=[];smoothRef.current.reset();calibrateRef.current=true;setCalibrating(true)
    baselineRef.current=null;setBaseline(null)
    streakRef.current={kind:'',since:0,reported:false}
    setStatus({kind:'calibrating',label:labelFor.calibrating,detail:'Look at the webcam lens steadily for about 2 seconds',faceCount:1})
  },[])
  useEffect(()=>{
    let disposed=false,intervalId=null,task=null
    if (!enabled || !stream) {
      setStatus(INITIAL);setEvents([]);setBaseline(null);setCalibrating(false)
      baselineRef.current=null;calibrateRef.current=false;samplesRef.current=[];smoothRef.current.reset()
      drawFaceGuides(canvasRef.current,videoRef.current,[])
      return
    }
    const updateStatus = (kind,detail,faceCount,now) => {
      if (now-lastUpdateRef.current>230 || kind==='error') {
        setStatus({kind,label:labelFor[kind]||kind,detail,faceCount});lastUpdateRef.current=now
      }
      const streak = streakRef.current
      if (streak.kind!==kind) {
        streakRef.current={kind,since:now,reported:false};return
      }
      if (sustainedMs[kind] && !streak.reported && now-streak.since>=sustainedMs[kind]) {
        streak.reported=true
        const info = {
          id:`${Date.now()}-${kind}`,kind,time:new Date().toLocaleTimeString(),
          durationSec:Math.round((now-streak.since)/1000),
          label: kind==='away'?'Possible gaze shift':kind==='no_face'?'Face temporarily missing':'More than one face'
        }
        setEvents(previous=>[info,...previous].slice(0,25))
      }
    }
    const init = async()=>{
      try {
        setStatus({kind:'loading',label:labelFor.loading,detail:'Loading local MediaPipe WASM and face model',faceCount:0})
        const {FaceLandmarker,FilesetResolver}=await import('@mediapipe/tasks-vision')
        const root=`${import.meta.env.BASE_URL}vision/`
        const vision=await FilesetResolver.forVisionTasks(`${root}wasm`)
        const options={baseOptions:{modelAssetPath:`${root}face_landmarker.task`,delegate:'GPU'},runningMode:'VIDEO',numFaces:2,minFaceDetectionConfidence:.5,minFacePresenceConfidence:.5,minTrackingConfidence:.5,outputFaceBlendshapes:false,outputFacialTransformationMatrixes:true}
        try {task=await FaceLandmarker.createFromOptions(vision,options)}
        catch {task=await FaceLandmarker.createFromOptions(vision,{...options,baseOptions:{...options.baseOptions,delegate:'CPU'}})}
        if(disposed){task.close();return}
        // After explicit local guidance consent, calibrate automatically on stable lens-facing samples.
        // A user can recalibrate manually if camera placement or lighting changes.
        samplesRef.current=[];calibrateRef.current=true;setCalibrating(true)
        setStatus({kind:'calibrating',label:labelFor.calibrating,detail:'Look at the camera lens for ~3 seconds to calibrate automatically',faceCount:0})
        let lastFrame=-1
        const analyze=()=>{
          const video=videoRef.current, canvas=canvasRef.current
          if (!video || video.readyState<2 || video.videoWidth<100 || !canvas || video.currentTime===lastFrame) return
          lastFrame=video.currentTime
          const now=performance.now()
          let result
          try {result=task.detectForVideo(video,now)}
          catch (e) {if(!disposed){setStatus({kind:'error',label:labelFor.error,detail:`Vision processing error: ${e.message}`,faceCount:0});clearInterval(intervalId)};return}
          const faces=result.faceLandmarks||[]
          drawFaceGuides(canvas,video,faces)
          if (faces.length===0) {updateStatus('no_face','Move into frame or improve lighting',0,now);return}
          if (faces.length>1) {updateStatus('multiple','More than one face is detected in the camera frame',faces.length,now);return}
          const measurement=measureGaze(faces[0],result.facialTransformationMatrixes?.[0])
          if (calibrateRef.current) {
            // Require consecutive usable frames; avoid accepting a baseline across long gaps.
            if (measurement) {
              if (lastCalibFrameRef.current && now-lastCalibFrameRef.current>650) samplesRef.current=[]
              lastCalibFrameRef.current=now
              samplesRef.current.push(measurement)
            }
            if (samplesRef.current.length>=24) {
              const ref = averageCalibration(samplesRef.current)
              calibrateRef.current=false;setCalibrating(false)
              if(ref){baselineRef.current=ref;setBaseline(ref);smoothRef.current.reset();updateStatus('center','Automatic lens reference captured locally. Recalibrate if needed',1,now)}
              else {samplesRef.current=[];calibrateRef.current=true;setCalibrating(true);updateStatus('calibrating','Calibration unstable. Keep facing the lens and stay relatively still',1,now)}
            } else updateStatus('calibrating',`${samplesRef.current.length}/24 stable frames · look at the webcam lens`,1,now)
            return
          }
          if (!measurement) {updateStatus('unknown','Eyes may be blinking, partly hidden or insufficiently lit',1,now);return}
          if (!baselineRef.current) {updateStatus('ready','Calibrate once before approximate gaze monitoring',1,now);return}
          const smoothed=smoothRef.current.push(measurement)
          const guess=classifyGaze(smoothed,baselineRef.current)
          updateStatus(guess.kind,guess.detail,1,now)
        }
        // 8Hz keeps CPU use manageable for ordinary Windows laptops.
        intervalId=setInterval(analyze,125)
      } catch(e) {
        if(!disposed){setStatus({kind:'error',label:labelFor.error,detail:`${e.message}. Run npm run setup:vision to download the model and WASM assets.`,faceCount:0})}
      }
    }
    init()
    return()=>{disposed=true;if(intervalId)clearInterval(intervalId);task?.close();drawFaceGuides(canvasRef.current,videoRef.current,[])}
  },[enabled,stream,videoRef,canvasRef])
  return {status,events,calibrating,calibrated:!!baseline,beginCalibration,clearEvents:()=>setEvents([])}
}
