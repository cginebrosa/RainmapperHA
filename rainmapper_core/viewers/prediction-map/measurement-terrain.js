// Distances use physical elevations, never camera pitch or terrain exaggeration.
const RADIUS = 6371008.8, RAD = Math.PI / 180;
export const MAX_DISTANCE = 50000;
export const MAX_WAYPOINTS = 100;
const DEM_ZOOM = 13, TILE_SIZE = 256, MAX_TILES = 48, CACHE_TILES = 32;

export function horizontalDistance(a, b) {
  const lat = (b[1] - a[1]) * RAD, lon = (b[0] - a[0]) * RAD;
  const h = Math.sin(lat / 2) ** 2 + Math.cos(a[1] * RAD) * Math.cos(b[1] * RAD) * Math.sin(lon / 2) ** 2;
  return 2 * RADIUS * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
}

export function lineCoordinates(a, b, segments = 1) {
  const angle = horizontalDistance(a, b) / RADIUS;
  const vector = p => [Math.cos(p[1] * RAD) * Math.cos(p[0] * RAD), Math.cos(p[1] * RAD) * Math.sin(p[0] * RAD), Math.sin(p[1] * RAD)];
  const av = vector(a), bv = vector(b), points = [];
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const u = angle < 1e-9 ? 1 - t : Math.sin((1 - t) * angle) / Math.sin(angle);
    const v = angle < 1e-9 ? t : Math.sin(t * angle) / Math.sin(angle);
    const [x, y, z] = av.map((n, j) => n * u + bv[j] * v);
    let lon = Math.atan2(y, x) / RAD;
    const previous = points.length ? points.at(-1)[0] : a[0];
    lon += 360 * Math.round((previous - lon) / 360);
    points.push([lon, Math.atan2(z, Math.hypot(x, y)) / RAD]);
  }
  points[0] = [...a];
  points[points.length - 1] = [b[0] + 360 * Math.round((points.at(-1)[0] - b[0]) / 360), b[1]];
  return points;
}

export function profileCoordinates(a, b) {
  if (![...a, ...b].every(Number.isFinite) || Math.abs(a[1]) > 85 || Math.abs(b[1]) > 85) throw Error('coverage');
  const distance = horizontalDistance(a, b);
  if (distance > MAX_DISTANCE) throw Error('limit');
  return lineCoordinates(a, b, Math.max(1, Math.ceil(distance / 25)));
}

export function pathDistance(points) {
  return points.slice(1).reduce((sum, point, i) => sum + horizontalDistance(points[i], point), 0);
}

// Preserve every bend, including a return to the starting point. Budget applies
// to the whole path, not separately to each leg.
export function pathCoordinates(points, maxSegments = 256, spacing = 100) {
  if (points.length < 2) return points.map(p => [...p]);
  const lengths = points.slice(1).map((p, i) => horizontalDistance(points[i], p));
  if (lengths.length > maxSegments) throw Error('limit');
  const total = lengths.reduce((a, b) => a + b, 0);
  if (lengths.reduce((sum, length) => sum + Math.max(1, Math.ceil(length / spacing)), 0) > maxSegments) {
    spacing = total / Math.max(1, maxSegments - lengths.length);
  }
  const coordinates = [[...points[0]]];
  lengths.forEach((length, i) => {
    const leg = lineCoordinates(coordinates.at(-1), points[i + 1], Math.max(1, Math.ceil(length / spacing)));
    coordinates.push(...leg.slice(1));
  });
  return coordinates;
}

export function pathProfileCoordinates(points) {
  if (points.length < 2 || points.length > MAX_WAYPOINTS) throw Error('limit');
  if (points.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite) || Math.abs(p[1]) > 85)) throw Error('coverage');
  if (pathDistance(points) > MAX_DISTANCE) throw Error('limit');
  return pathCoordinates(points, 2000, 25);
}

export function summarizeProfile(points, elevations) {
  if (points.length !== elevations.length || points.length < 2 || !elevations.every(Number.isFinite)) throw Error('missing');
  let horizontal = 0, terrain = 0, ascent = 0, descent = 0;
  for (let i = 1; i < points.length; i++) {
    const length = horizontalDistance(points[i - 1], points[i]), change = elevations[i] - elevations[i - 1];
    horizontal += length; terrain += Math.hypot(length, change);
    ascent += Math.max(0, change); descent += Math.max(0, -change);
  }
  return {horizontal, terrain, ascent, descent, change: elevations.at(-1) - elevations[0]};
}

export function createTerrainSampler(template, fetchTile = (...args) => fetch(...args)) {
  const cache = new Map();
  const scale = 2 ** DEM_ZOOM, pixels = scale * TILE_SIZE;
  function pixel(lon, lat) {
    return [((lon + 180) / 360 * pixels) - .5,
      (1 - Math.asinh(Math.tan(lat * RAD)) / Math.PI) / 2 * pixels - .5];
  }
  function cell(x, y) {
    x = ((x % pixels) + pixels) % pixels; y = Math.max(0, Math.min(pixels - 1, y));
    const tx = Math.floor(x / TILE_SIZE), ty = Math.floor(y / TILE_SIZE);
    return {key: `${tx}/${ty}`, x: tx, y: ty, offset: 4 * ((y % TILE_SIZE) * TILE_SIZE + x % TILE_SIZE)};
  }
  async function load(tile, signal) {
    if (cache.has(tile.key)) {
      const data = cache.get(tile.key); cache.delete(tile.key); cache.set(tile.key, data); return data;
    }
    const url = template.replace('{z}', DEM_ZOOM).replace('{x}', tile.x).replace('{y}', tile.y);
    const response = await fetchTile(url, {signal, credentials: 'omit'});
    if (!response.ok) throw Error('unavailable');
    const blob = await response.blob();
    if (blob.size > 2 * 1024 * 1024) throw Error('tile_limit');
    const bitmap = await createImageBitmap(blob);
    try {
      if (bitmap.width !== TILE_SIZE || bitmap.height !== TILE_SIZE) throw Error('invalid_tile');
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = TILE_SIZE;
      const context = canvas.getContext('2d', {willReadFrequently: true});
      context.drawImage(bitmap, 0, 0);
      const data = context.getImageData(0, 0, TILE_SIZE, TILE_SIZE).data;
      signal.throwIfAborted();
      cache.set(tile.key, data);
      while (cache.size > CACHE_TILES) cache.delete(cache.keys().next().value);
      return data;
    } finally { bitmap.close(); }
  }
  return {
    clear() { cache.clear(); },
    async sample(points, signal) {
      signal.throwIfAborted();
      if (points.length > 2001) throw Error('limit');
      const tiles = new Map();
      const samples = points.map(([lon, lat]) => {
        if (!Number.isFinite(lon) || !Number.isFinite(lat) || Math.abs(lat) > 85) throw Error('coverage');
        const [x, y] = pixel(lon, lat), ix = Math.floor(x), iy = Math.floor(y);
        const cells = [cell(ix, iy), cell(ix + 1, iy), cell(ix, iy + 1), cell(ix + 1, iy + 1)];
        for (const c of cells) {
          tiles.set(c.key, c);
          if (tiles.size > MAX_TILES) throw Error('limit');
        }
        return {cells, dx: x - ix, dy: y - iy};
      });
      // Deduplicate and bound all requests before loading; at most four in flight.
      const queue = [...tiles.values()], loaded = new Map(); let next = 0;
      await Promise.all(Array.from({length: Math.min(4, queue.length)}, async () => {
        while (next < queue.length) {
          signal.throwIfAborted();
          const tile = queue[next++]; loaded.set(tile.key, await load(tile, signal));
        }
      }));
      signal.throwIfAborted();
      return samples.map(({cells, dx, dy}) => {
        const z = cells.map(({key, offset}) => {
          const data = loaded.get(key);
          if (data[offset + 3] !== 255) throw Error('missing');
          const value = data[offset] * 256 + data[offset + 1] + data[offset + 2] / 256 - 32768;
          if (value < -12000 || value > 9000) throw Error('missing');
          return value;
        });
        return (z[0] * (1 - dx) + z[1] * dx) * (1 - dy) + (z[2] * (1 - dx) + z[3] * dx) * dy;
      });
    },
  };
}
