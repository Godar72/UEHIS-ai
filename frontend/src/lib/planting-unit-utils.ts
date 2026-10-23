import crypto from 'crypto';

export const PU_NAMESPACE = '49e464c3-0db8-5061-a5ff-945f95238334';

export function uuidv5(namespace: string, name: string): string {
  const nsBytes = Buffer.from(namespace.replace(/-/g, ''), 'hex');
  const hash = crypto.createHash('sha1').update(nsBytes).update(name).digest();
  hash[6] = (hash[6] & 0x0f) | 0x50; // version 5
  hash[8] = (hash[8] & 0x3f) | 0x80; // variant
  const hex = hash.subarray(0, 16).toString('hex');
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-');
}

export function isUtm43n(x: number, y: number): boolean {
  // Valid projected bounds for UTM Zone 43N in the Pune study area:
  // Easting: 100,000 to 900,000 m (Pune dataset spans ~368,000 - 397,000 m)
  // Northing: 1,000,000 to 3,000,000 m (Pune dataset spans ~2,038,000 - 2,060,000 m)
  return (
    typeof x === 'number' &&
    typeof y === 'number' &&
    !isNaN(x) &&
    !isNaN(y) &&
    x >= 100000 &&
    x <= 900000 &&
    y >= 1000000 &&
    y <= 3000000
  );
}

/**
 * Strictly validates that an explicitly declared Coordinate Reference System (CRS)
 * identifier is a documented, authoritative representation of EPSG:32643 (UTM Zone 43N).
 *
 * Supported formats (case-insensitive, trimmed):
 * - Short code: "EPSG:32643", "EPSG::32643", "32643", or numeric 32643
 * - OGC URN: "urn:ogc:def:crs:EPSG::32643", "urn:ogc:def:crs:EPSG:32643", "urn:ogc:def:crs:EPSG:<version>:32643"
 * - OGC URI: "http(s)://www.opengis.net/def/crs/EPSG/0/32643", "http(s)://www.opengis.net/gml/srs/epsg.xml#32643"
 *
 * Rejects:
 * - Substring traps (e.g., "EPSG:132643", "MYCRS_32643", "CUSTOM_32643_PROJECTED")
 * - Incompatible CRSs (e.g., "EPSG:4326", "EPSG:3857", "EPSG:32644", "CRS84")
 * - Malformed, empty, or non-matching inputs
 */
export function isValidUtm43nCrs(crsIdentifier: unknown): boolean {
  if (crsIdentifier === 32643) return true;
  if (typeof crsIdentifier !== 'string') return false;

  const trimmed = crsIdentifier.trim();
  if (!trimmed) return false;

  const utm43nPattern =
    /^(?:(?:urn:ogc:def:crs:EPSG:(?:[0-9.]*:)?|EPSG:{1,2}|https?:\/\/www\.opengis\.net\/(?:def\/crs\/EPSG\/0\/|gml\/srs\/epsg\.xml#))?32643)$/i;

  return utm43nPattern.test(trimmed);
}

export function parseCoordinates(geom: unknown): [number, number] | null {
  if (!geom) return null;
  // 1. GeoJSON object format: { type: 'Point', coordinates: [x, y] }
  if (typeof geom === 'object' && geom !== null && 'coordinates' in geom) {
    const obj = geom as {
      type?: string;
      coordinates?: unknown;
      crs?: { properties?: { name?: unknown; code?: unknown } } | string | null;
    };
    if (obj.crs != null) {
      const crsId =
        typeof obj.crs === 'string'
          ? obj.crs
          : (obj.crs.properties?.name ?? obj.crs.properties?.code);
      if (!isValidUtm43nCrs(crsId)) {
        return null;
      }
    }
    const coords = obj.coordinates;
    if (Array.isArray(coords) && coords.length >= 2) {
      const x = Number(coords[0]);
      const y = Number(coords[1]);
      if (isUtm43n(x, y)) return [x, y];
    }
  }
  // 2. String representation (JSON, WKT, or PostGIS EWKB hex)
  if (typeof geom === 'string') {
    const str = geom.trim();
    if (str.startsWith('{')) {
      try {
        const parsed = JSON.parse(str);
        if (parsed.crs != null) {
          const crsId =
            typeof parsed.crs === 'string'
              ? parsed.crs
              : (parsed.crs.properties?.name ?? parsed.crs.properties?.code);
          if (!isValidUtm43nCrs(crsId)) {
            return null;
          }
        }
        if (parsed.coordinates && Array.isArray(parsed.coordinates) && parsed.coordinates.length >= 2) {
          const x = Number(parsed.coordinates[0]);
          const y = Number(parsed.coordinates[1]);
          if (isUtm43n(x, y)) return [x, y];
        }
      } catch {
        // Not valid JSON
      }
    }
    // Check WKT / EWKT: e.g. "SRID=32643;POINT(385000 2045000)" or "POINT(385000 2045000)"
    const sridMatch = str.match(/SRID\s*=\s*([^\s;]+)\s*;/i);
    if (sridMatch && !isValidUtm43nCrs(sridMatch[1])) {
      return null; // Reject explicit non-32643 SRID
    }
    const wktMatch = str.match(/POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)/i);
    if (wktMatch) {
      const x = Number(wktMatch[1]);
      const y = Number(wktMatch[2]);
      if (isUtm43n(x, y)) return [x, y];
    }
    // Check PostGIS EWKB hex string
    if (/^[0-9a-fA-F]{42,}$/.test(str)) {
      try {
        const buf = Buffer.from(str, 'hex');
        const isLittleEndian = buf.readUInt8(0) === 1;
        const typeInt = isLittleEndian ? buf.readUInt32LE(1) : buf.readUInt32BE(1);
        const geomType = typeInt & 0x1f;
        if (geomType !== 1) return null; // Must be Point
        const hasSrid = (typeInt & 0x20000000) !== 0;
        if (hasSrid) {
          const srid = isLittleEndian ? buf.readUInt32LE(5) : buf.readUInt32BE(5);
          if (srid !== 32643 && srid !== 0) return null; // Reject non-32643 SRID
        }
        const coordOffset = hasSrid ? 9 : 5;
        if (buf.length >= coordOffset + 16) {
          const x = isLittleEndian ? buf.readDoubleLE(coordOffset) : buf.readDoubleBE(coordOffset);
          const y = isLittleEndian ? buf.readDoubleLE(coordOffset + 8) : buf.readDoubleBE(coordOffset + 8);
          if (isUtm43n(x, y)) return [x, y];
        }
      } catch {
        // Hex parse failed
      }
    }
  }
  return null;
}
