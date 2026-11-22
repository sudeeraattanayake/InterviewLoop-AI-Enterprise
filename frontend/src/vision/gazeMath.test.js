import test from 'node:test'
import assert from 'node:assert/strict'
import {averageCalibration,classifyGaze,measureGaze} from './gazeMath.js'

test('does not pretend to measure missing landmarks',()=>{
 assert.equal(measureGaze([]),null)
 assert.equal(measureGaze(Array.from({length:478},()=>null)),null)
})
test('rejects too few and unstable calibration frames',()=>{
 assert.equal(averageCalibration([{x:.5,y:.5,head:0}]),null)
 assert.equal(averageCalibration(Array.from({length:16},(_,i)=>({x:i%2?1:0,y:.5,head:0}))),null)
})
test('calibrates and classifies iris/head displacement conservatively',()=>{
 const samples=Array.from({length:16},()=>({x:.5,y:.5,head:0}))
 const baseline=averageCalibration(samples)
 assert.deepEqual(baseline,{x:.5,y:.5,head:0})
 assert.equal(classifyGaze({x:.52,y:.51,head:.01},baseline).kind,'center')
 assert.equal(classifyGaze({x:.85,y:.5,head:0},baseline).kind,'away')
 assert.equal(classifyGaze({x:.5,y:.5,head:.25},baseline).kind,'away')
 assert.equal(classifyGaze(null,baseline).kind,'unknown')
})

test('computes normalized iris movement from synthetic facial landmarks',()=>{
 const l=Array.from({length:478},()=>({x:.5,y:.5}))
 l[33]={x:.20,y:.4};l[133]={x:.38,y:.4};l[159]={x:.29,y:.38};l[145]={x:.29,y:.44};l[468]={x:.29,y:.41}
 l[362]={x:.62,y:.4};l[263]={x:.80,y:.4};l[386]={x:.71,y:.38};l[374]={x:.71,y:.44};l[473]={x:.71,y:.41}
 l[1]={x:.5,y:.5};l[234]={x:.1,y:.5};l[454]={x:.9,y:.5}
 const m=measureGaze(l)
 assert.ok(m);assert.ok(Math.abs(m.x-.5)<.01);assert.ok(Math.abs(m.y-.5)<.01)
 l[468]={x:.34,y:.41};l[473]={x:.76,y:.41}
 assert.ok(measureGaze(l).x>.7)
})

import {measureHeadPose} from './gazeMath.js'
import {TemporalGazeFilter} from './temporalFilter.js'

test('reads neutral and rotated head pose from optional column-major matrix',()=>{
 const neutral={data:[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]}
 const pose=measureHeadPose(neutral)
 assert.ok(pose && Math.abs(pose.yaw)<.001 && Math.abs(pose.pitch)<.001)
 const rotated={data:[.866,0,-.5,0, 0,1,0,0, .5,0,.866,0, 0,0,0,1]}
 assert.ok(measureHeadPose(rotated).yaw>20)
 assert.equal(measureHeadPose({data:[0]}),null)
})
test('smoothing rejects isolated outlier frames and resets between camera sessions',()=>{
 const smoother=new TemporalGazeFilter(5)
 for(let i=0;i<4;i++) smoother.push({x:.5,y:.5,head:0,yaw:0,pitch:0,roll:0})
 const smoothed=smoother.push({x:.96,y:.5,head:0,yaw:25,pitch:0,roll:0})
 assert.equal(smoothed.x,.5)
 assert.equal(smoothed.yaw,0)
 smoother.reset()
 assert.equal(smoother.push({x:.9,y:.5,head:0}).x,.9)
})
test('head pose monitoring remains conservative after stable calibration',()=>{
 const s={x:.5,y:.5,head:0,yaw:0,pitch:0,roll:0}
 const baseline=averageCalibration(Array.from({length:24},()=>s))
 assert.equal(classifyGaze({...s,yaw:12},baseline).kind,'center')
 assert.equal(classifyGaze({...s,yaw:28},baseline).kind,'away')
})
