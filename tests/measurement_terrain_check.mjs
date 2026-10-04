// Analytical distances and bounded DEM sampling; no network or operational data.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const source = await fs.readFile(new URL('../rainmapper_core/viewers/prediction-map/measurement-terrain.js', import.meta.url), 'utf8');
const {horizontalDistance, profileCoordinates, pathDistance, pathCoordinates, pathProfileCoordinates, summarizeProfile, createTerrainSampler} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const near = (actual, expected, tolerance = 1e-6) => assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);
near(horizontalDistance([0, 0], [1, 0]), 111195.080233533, .001);
const degree = 1000 / 111195.080233533;
const points = [[0, 0], [degree / 2, 0], [degree, 0]];
near(summarizeProfile(points, [100, 100, 100]).terrain, 1000);
const ridge = summarizeProfile(points, [100, 600, 100]);
near(ridge.terrain, Math.sqrt(2) * 1000); near(ridge.ascent, 500); near(ridge.descent, 500); near(ridge.change, 0);
near(summarizeProfile(points, [0, 500, 1000]).terrain, ridge.terrain);
near(summarizeProfile(points, [0, 500, 1000]).change, 1000);
assert.throws(() => summarizeProfile(points, [0, null, 0]), /missing/);
assert.throws(() => profileCoordinates([0, 0], [1, 0]), /limit/);
assert.throws(() => profileCoordinates([0, 86], [0, 86]), /coverage/);
const sample = profileCoordinates([0, 0], [degree, 0]);
assert.ok(sample.length <= 42 && sample.length >= 41);
for (let i = 1; i < sample.length; i++) assert.ok(horizontalDistance(sample[i - 1], sample[i]) <= 25.001);
const wrapped = profileCoordinates([179.999, 42], [-179.999, 42]);
assert.ok(wrapped.at(-1)[0] > 180); assert.ok(horizontalDistance(wrapped[0], wrapped.at(-1)) < 200);
near(summarizeProfile(profileCoordinates([2, 42], [2, 42]), [0, 0]).terrain, 0);

const returnPath = [[0, 0], [degree, 0], [0, 0]];
near(pathDistance(returnPath), 2000);
const returnSamples = pathProfileCoordinates(returnPath);
near(summarizeProfile(returnSamples, returnSamples.map(() => 100)).terrain, 2000);
assert.ok(returnSamples.some(p => p[0] === degree && p[1] === 0), 'Do not cut across intermediate waypoints');
near(summarizeProfile(returnPath, [100, 600, 100]).terrain, 2 * Math.hypot(1000, 500));
assert.throws(() => pathProfileCoordinates([[0, 0], [.3, 0], [0, 0]]), /limit/, 'The 50 km limit applies to the complete route');
assert.throws(() => pathProfileCoordinates(Array.from({length:101}, () => [0,0])), /limit/);
const manyBends = Array.from({length:100}, (_, i) => [.448 * i / 99, i % 2 * .0001]);
const densePath = pathProfileCoordinates(manyBends);
assert.ok(densePath.length <= 2001 && pathDistance(manyBends) < 50000);
for (const p of manyBends) assert.ok(densePath.some(q => Math.abs(p[0] - q[0]) < 1e-10 && Math.abs(p[1] - q[1]) < 1e-10));
assert.ok(pathCoordinates(manyBends).length <= 257, 'Display geometry stays bounded across many legs');
const wrappedPath = pathProfileCoordinates([[179.999,42],[-179.999,42],[179.999,42]]);
assert.ok(wrappedPath.some(p => p[0] > 180));
for (let i=1;i<wrappedPath.length;i++) assert.ok(Math.abs(wrappedPath[i][0]-wrappedPath[i-1][0])<.01);

// Model a PNG decoder with a continuous planar elevation across adjacent tiles.
let closed = 0, requests = 0, inFlight = 0, peak = 0, alpha = 255;
globalThis.createImageBitmap = async blob => ({...JSON.parse(await blob.text()), width:256, height:256, close() { closed++; }});
globalThis.document = {createElement() { let image; return {getContext() { return {
  drawImage(value) { image = value; },
  getImageData() {
    const data = new Uint8ClampedArray(256 * 256 * 4);
    for (let x = 0; x < 256; x++) for (let y = 0; y < 256; y++) {
      const height = 100 + (image.x - 4096) * 256 + x, encoded = height + 32768, at = (y * 256 + x) * 4;
      data[at] = Math.floor(encoded / 256); data[at + 1] = encoded % 256; data[at + 2] = 0; data[at + 3] = alpha;
    }
    return {data};
  },
}; }}; }};
const sampler = createTerrainSampler('https://fixture/{z}/{x}/{y}', async (url, {signal}) => {
  signal.throwIfAborted(); requests++; inFlight++; peak = Math.max(peak, inFlight);
  await new Promise(resolve => setTimeout(resolve, 1)); inFlight--;
  const [, , , , x, y] = url.split('/');
  return {ok:true, blob:async () => new Blob([JSON.stringify({x:Number(x), y:Number(y)})])};
});
const longitude = pixel => (4096 * 256 + pixel + .5) / (8192 * 256) * 360 - 180;
const controller = new AbortController();
const elevations = await sampler.sample([[longitude(255.25), 0], [longitude(255.75), 0]], controller.signal);
near(elevations[0], 355.25); near(elevations[1], 355.75);
assert.equal(requests, 4, 'Two adjacent pixels straddling four tiles reuse one request per tile');
assert.equal(closed, requests); assert.ok(peak <= 4);
await sampler.sample([[longitude(255.25), 0]], controller.signal); assert.equal(requests, 4);
controller.abort(); await assert.rejects(sampler.sample([[0,0]], controller.signal), {name:'AbortError'});
const signal = new AbortController().signal;
await assert.rejects(sampler.sample(Array.from({length:2002}, () => [0,0]), signal), /limit/);
assert.equal(requests, 4, 'Oversized profiles are rejected before downloading');
sampler.clear(); alpha = 0;
await assert.rejects(sampler.sample([[longitude(255.25),0]], signal), /missing/);
console.log('PASS measurement: paths/returns/bends/global limits, horizontal/terrain/ridge/zero/dateline, sample bounds, bilinear tile seams, caching, cancellation, missing DEM and request bounds');
