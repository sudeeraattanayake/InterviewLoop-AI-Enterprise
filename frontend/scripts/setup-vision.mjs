/** Fetch local model once and copy the exact locally installed WASM runtime. No CDN runtime dependency. */
import {mkdir,stat,cp,writeFile,rename} from 'node:fs/promises'
import {join,resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..')
const source=join(root,'node_modules/@mediapipe/tasks-vision/wasm')
const wasm=join(root,'public/vision/wasm')
const model=join(root,'public/vision/face_landmarker.task')
const url='https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'
const exists=async p=>{try{await stat(p);return true}catch{return false}}
if (!(await exists(source))) throw Error('Install npm dependencies first: npm install')
await mkdir(wasm,{recursive:true})
await cp(source,wasm,{recursive:true,force:true})
console.log('Copied local MediaPipe WASM runtime.')
if (!(await exists(model))) {
 console.log('Downloading official MediaPipe face landmarker model (one time, ~3.6MB)...')
 let res
 try {res=await fetch(url,{signal:AbortSignal.timeout(90000)})}
 catch(e){throw Error(`Cannot download MediaPipe model: ${e.message}. Check your connection and run npm run setup:vision again.`)}
 if(!res.ok)throw Error(`Model download failed HTTP ${res.status}`)
 const data=Buffer.from(await res.arrayBuffer())
 if(data.length<1_000_000 || data.length>25_000_000)throw Error('Unexpected model download size; refusing to write corrupted file')
 await writeFile(`${model}.partial`,data)
 await rename(`${model}.partial`,model)
}
console.log('Face detection ready: local model + local WASM. No webcam data is uploaded by this setup.')
