/* Recognise regular Mercator (TerraDraw) and WGS84 (GBIF) rings, without changing
 * persisted GeoJSON or interpreting arbitrary rounded polygons as circles. */
(() => {
  'use strict';
  const R = 6378137, radians = Math.PI / 180;
  const project = ([lon, lat]) => [R * lon * radians, R * Math.log(Math.tan(Math.PI / 4 + lat * radians / 2))];
  const unproject = ([x, y]) => [x / R / radians, (2 * Math.atan(Math.exp(y / R)) - Math.PI / 2) / radians];
  // Vincenty's WGS84 direct/inverse solutions. Bounded iterations: a geometry
  // that cannot be recognised safely stays an ordinary editable polygon.
  const flattening = 1 / 298.257223563, minor = R * (1 - flattening);
  function coefficients(cosSqAlpha) {
    const u = cosSqAlpha * (R * R - minor * minor) / (minor * minor);
    return [1 + u / 16384 * (4096 + u * (-768 + u * (320 - 175 * u))),
      u / 1024 * (256 + u * (-128 + u * (74 - 47 * u)))];
  }
  const correction = (B, sinSigma, cosSigma, cos2) => B * sinSigma * (cos2 + B / 4 *
    (cosSigma * (-1 + 2 * cos2 * cos2) - B / 6 * cos2 * (-3 + 4 * sinSigma * sinSigma) * (-3 + 4 * cos2 * cos2)));
  function inverse(start, end) {
    const U1 = Math.atan((1 - flattening) * Math.tan(start[1] * radians));
    const U2 = Math.atan((1 - flattening) * Math.tan(end[1] * radians));
    const s1 = Math.sin(U1), c1 = Math.cos(U1), s2 = Math.sin(U2), c2 = Math.cos(U2);
    const L = (end[0] - start[0]) * radians;
    let lambda = L;
    for (let i = 0; i < 50; i++) {
      const sl = Math.sin(lambda), cl = Math.cos(lambda);
      const sinSigma = Math.hypot(c2 * sl, c1 * s2 - s1 * c2 * cl);
      if (!sinSigma) return {distance: 0, bearing: 0};
      const cosSigma = s1 * s2 + c1 * c2 * cl, sigma = Math.atan2(sinSigma, cosSigma);
      const sinAlpha = c1 * c2 * sl / sinSigma, cosSqAlpha = 1 - sinAlpha * sinAlpha;
      const cos2 = cosSqAlpha > 1e-15 ? cosSigma - 2 * s1 * s2 / cosSqAlpha : 0;
      const C = flattening / 16 * cosSqAlpha * (4 + flattening * (4 - 3 * cosSqAlpha));
      const next = L + (1 - C) * flattening * sinAlpha * (sigma + C * sinSigma * (cos2 + C * cosSigma * (-1 + 2 * cos2 * cos2)));
      if (Math.abs(next - lambda) < 1e-13) {
        const [A, B] = coefficients(cosSqAlpha);
        return {distance: minor * A * (sigma - correction(B, sinSigma, cosSigma, cos2)),
          bearing: Math.atan2(c2 * sl, c1 * s2 - s1 * c2 * cl)};
      }
      lambda = next;
    }
    return null;
  }
  function direct(start, distance, bearing) {
    const U = Math.atan((1 - flattening) * Math.tan(start[1] * radians));
    const sU = Math.sin(U), cU = Math.cos(U), sb = Math.sin(bearing), cb = Math.cos(bearing);
    const sigma1 = Math.atan2(Math.tan(U), cb), sinAlpha = cU * sb, cosSqAlpha = 1 - sinAlpha * sinAlpha;
    const [A, B] = coefficients(cosSqAlpha), base = distance / (minor * A);
    let sigma = base;
    for (let i = 0; i < 50; i++) {
      const next = base + correction(B, Math.sin(sigma), Math.cos(sigma), Math.cos(2 * sigma1 + sigma));
      if (Math.abs(next - sigma) < 1e-13) {sigma = next; break;}
      sigma = next;
    }
    const ss = Math.sin(sigma), cs = Math.cos(sigma), cos2 = Math.cos(2 * sigma1 + sigma);
    const tmp = sU * ss - cU * cs * cb;
    const lat = Math.atan2(sU * cs + cU * ss * cb, (1 - flattening) * Math.hypot(sinAlpha, tmp));
    const lambda = Math.atan2(ss * sb, cU * cs - sU * ss * cb);
    const C = flattening / 16 * cosSqAlpha * (4 + flattening * (4 - 3 * cosSqAlpha));
    const L = lambda - (1 - C) * flattening * sinAlpha * (sigma + C * ss * (cos2 + C * cs * (-1 + 2 * cos2 * cos2)));
    return [((start[0] + L / radians + 540) % 360) - 180, lat / radians];
  }
  function recognise(geometry) {
    if (geometry?.type !== 'Polygon' || geometry.coordinates.length !== 1) return null;
    const ring = geometry.coordinates[0], count = ring.length - 1;
    if (count < 32 || ring[0][0] !== ring[count][0] || ring[0][1] !== ring[count][1]) return null;
    if (ring.some(p => p.length !== 2 || !p.every(Number.isFinite) || Math.abs(p[1]) >= 85)) return null;
    return recogniseMercator(ring, count) || recogniseGeodesic(ring, count);
  }
  function recogniseGeodesic(ring, count) {
    if (count % 2) return null;
    const diameter = inverse(ring[0], ring[count / 2]);
    if (!diameter || diameter.distance < 0.01 || diameter.distance > 200000) return null;
    const center = direct(ring[0], diameter.distance / 2, diameter.bearing);
    const points = ring.slice(0, -1).map(p => inverse(center, p));
    if (points.some(p => !p)) return null;
    const radiusMeters = points.reduce((sum, p) => sum + p.distance / count, 0);
    const angle = points[0].bearing, direction = Math.sign(Math.sin(points[1].bearing - angle));
    const tolerance = Math.max(0.002, radiusMeters * 1e-7);
    if (!direction || points.some((p, i) => {
      const expected = angle + direction * 2 * Math.PI * i / count;
      return Math.hypot(p.distance * Math.sin(p.bearing) - radiusMeters * Math.sin(expected),
        p.distance * Math.cos(p.bearing) - radiusMeters * Math.cos(expected)) > tolerance;
    })) return null;
    return {center, radiusMeters, count, angle, direction, geodesic: true};
  }
  function recogniseMercator(ring, count) {
    const points = ring.slice(0, -1).map(project);
    const center = points.reduce((sum, p) => [sum[0] + p[0] / count, sum[1] + p[1] / count], [0, 0]);
    const radii = points.map(p => Math.hypot(p[0] - center[0], p[1] - center[1]));
    const radius = radii.reduce((a, b) => a + b, 0) / count;
    // TerraDraw persists nine decimal places. Allow rounding, not edited vertices.
    const tolerance = Math.max(0.002, radius * 1e-7);
    if (radius <= tolerance || radii.some(r => Math.abs(r - radius) > tolerance)) return null;
    const angle = Math.atan2(points[0][1] - center[1], points[0][0] - center[0]);
    const cross = (points[0][0] - center[0]) * (points[1][1] - center[1]) - (points[0][1] - center[1]) * (points[1][0] - center[0]);
    const direction = Math.sign(cross);
    if (!direction || points.some((p, i) => {
      const a = angle + direction * 2 * Math.PI * i / count;
      return Math.hypot(p[0] - center[0] - radius * Math.cos(a), p[1] - center[1] - radius * Math.sin(a)) > tolerance;
    })) return null;
    const location = unproject(center);
    return {center: location, radiusMeters: radius * Math.cos(location[1] * radians), count, angle, direction};
  }
  function edge(circle) {
    if (circle.geodesic) return direct(circle.center, circle.radiusMeters, Math.PI / 2);
    const center = project(circle.center);
    return unproject([center[0] + circle.radiusMeters / Math.cos(circle.center[1] * radians), center[1]]);
  }
  function radiusAt(circle, location) {
    if (circle.geodesic) return inverse(circle.center, location)?.distance ?? NaN;
    const a = project(circle.center), b = project(location);
    return Math.hypot(b[0] - a[0], b[1] - a[1]) * Math.cos(circle.center[1] * radians);
  }
  function geometry(circle) {
    const center = project(circle.center), radius = circle.radiusMeters / Math.cos(circle.center[1] * radians);
    const ring = Array.from({length: circle.count}, (_, i) => {
      const a = circle.angle + circle.direction * 2 * Math.PI * i / circle.count;
      if (circle.geodesic) return direct(circle.center, circle.radiusMeters, a).map(v => Number(v.toFixed(9)));
      return unproject([center[0] + radius * Math.cos(a), center[1] + radius * Math.sin(a)]).map(v => Number(v.toFixed(9)));
    });
    ring.push([...ring[0]]);
    return {type: 'Polygon', coordinates: [ring]};
  }
  window.RainmapperSiteCircles = {recognise, geometry, edge, radiusAt};
})();
