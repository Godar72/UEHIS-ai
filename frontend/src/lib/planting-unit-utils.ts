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
 * - Legacy OGC URN: "urn:x-ogc:def:crs:EPSG::32643"
 * - OGC URI: "http(s)://www.opengis.net/def/crs/EPSG/<version>/32643", "http(s)://www.opengis.net/gml/srs/epsg.xml#32643"
 * - GeoJSON CRS object: { type: 'name', properties: { name: '...' } } or { properties: { code: 32643 } }
 *
 * Rejects:
 * - Substring traps (e.g., "EPSG:132643", "MYCRS_32643", "CUSTOM_32643_PROJECTED", "32643_CUSTOM")
 * - Incompatible CRSs (e.g., "EPSG:4326", "EPSG:3857", "EPSG:32644", "CRS84")
 * - Malformed, empty, or non-matching inputs
 */
export function isValidUtm43nCrs(crsIdentifier: unknown): boolean {
  if (crsIdentifier === 32643) return true;
  if (!crsIdentifier) return false;

  let identifierStr: unknown = crsIdentifier;
  if (typeof crsIdentifier === 'object' && crsIdentifier !== null) {
    const crsObj = crsIdentifier as {
      type?: unknown;
      properties?: { name?: unknown; code?: unknown };
    };
    identifierStr = crsObj.properties?.name ?? crsObj.properties?.code;
    if (identifierStr === 32643) return true;
  }

  if (typeof identifierStr !== 'string') return false;

  const trimmed = identifierStr.trim();
  if (!trimmed) return false;

  const utm43nPattern =
    /^(?:(?:urn:(?:x-)?ogc:def:crs:EPSG:(?:[0-9.]*:)?|EPSG:{1,2}|https?:\/\/www\.opengis\.net\/(?:def\/crs\/EPSG\/(?:[0-9.]*\/)?|gml\/srs\/epsg\.xml#))?32643)$/i;

  return utm43nPattern.test(trimmed);
}

export function parseCoordinates(geom: unknown): [number, number] | null {
  if (!geom) return null;

  // 1. GeoJSON object format: { type: 'Point', coordinates: [x, y], crs?: ... }
  if (typeof geom === 'object' && geom !== null && 'coordinates' in geom) {
    const obj = geom as {
      type?: unknown;
      coordinates?: unknown;
      crs?: unknown;
    };

    // Enforce Point geometry type
    if (typeof obj.type !== 'string' || obj.type.trim().toLowerCase() !== 'point') {
      return null;
    }

    // If explicit CRS is present, it must be valid EPSG:32643
    if (obj.crs != null && !isValidUtm43nCrs(obj.crs)) {
      return null;
    }

    const coords = obj.coordinates;
    if (Array.isArray(coords) && coords.length >= 2) {
      const x = Number(coords[0]);
      const y = Number(coords[1]);
      if (Number.isFinite(x) && Number.isFinite(y) && isUtm43n(x, y)) {
        return [x, y];
      }
    }
    return null;
  }

  // 2. String representation (JSON string, WKT/EWKT, or PostGIS EWKB hex)
  if (typeof geom === 'string') {
    const str = geom.trim();
    if (!str) return null;

    // 2.1 GeoJSON JSON string
    if (str.startsWith('{')) {
      try {
        const parsed = JSON.parse(str);
        if (typeof parsed === 'object' && parsed !== null && 'coordinates' in parsed) {
          // Enforce Point geometry type
          if (typeof parsed.type !== 'string' || parsed.type.trim().toLowerCase() !== 'point') {
            return null;
          }

          // If explicit CRS is present, it must be valid EPSG:32643
          if (parsed.crs != null && !isValidUtm43nCrs(parsed.crs)) {
            return null;
          }

          const coords = parsed.coordinates;
          if (Array.isArray(coords) && coords.length >= 2) {
            const x = Number(coords[0]);
            const y = Number(coords[1]);
            if (Number.isFinite(x) && Number.isFinite(y) && isUtm43n(x, y)) {
              return [x, y];
            }
          }
        }
        return null;
      } catch {
        return null;
      }
    }

    // 2.2 WKT / EWKT Point: e.g. "SRID=32643;POINT(385000 2045000)" or "POINT(385000 2045000)"
    const wktPattern = /^(?:SRID\s*=\s*([^;]+)\s*;\s*)?POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)$/i;
    const wktMatch = str.match(wktPattern);
    if (wktMatch) {
      const sridDecl = wktMatch[1];
      if (sridDecl !== undefined && !isValidUtm43nCrs(sridDecl)) {
        return null; // Reject explicit non-32643 SRID
      }
      const x = Number(wktMatch[2]);
      const y = Number(wktMatch[3]);
      if (Number.isFinite(x) && Number.isFinite(y) && isUtm43n(x, y)) {
        return [x, y];
      }
      return null;
    }

    // Explicit rejection if string attempted SRID or POINT with invalid/unsupported geometry
    if (/^SRID\s*=/i.test(str) || /\bPOINT\b/i.test(str)) {
      return null;
    }

    // 2.3 PostGIS EWKB hex string
    if (/^[0-9a-fA-F]+$/.test(str) && str.length % 2 === 0) {
      try {
        const buf = Buffer.from(str, 'hex');
        // Minimum 5 bytes: 1 byte byte-order + 4 bytes type
        if (buf.length < 5) return null;

        // Byte order: 0 (Big-Endian/XDR) or 1 (Little-Endian/NDR)
        const byteOrder = buf.readUInt8(0);
        if (byteOrder !== 0 && byteOrder !== 1) return null;
        const isLittleEndian = byteOrder === 1;

        // Geometry type integer
        const typeInt = isLittleEndian ? buf.readUInt32LE(1) : buf.readUInt32BE(1);
        const geomType = typeInt & 0x1f;
        if (geomType !== 1) return null; // Must be Point

        // EWKB flags: only SRID (0x20000000) allowed for standard 2D Point
        if ((typeInt & 0xdfffffe0) !== 0) return null;

        const hasSrid = (typeInt & 0x20000000) !== 0;
        let coordOffset = 5;

        if (hasSrid) {
          if (buf.length < 9) return null;
          const srid = isLittleEndian ? buf.readUInt32LE(5) : buf.readUInt32BE(5);
          if (srid !== 32643 && srid !== 0) return null;
          coordOffset = 9;
        }

        // Exact length check for 2D Point (2 doubles = 16 bytes)
        if (buf.length !== coordOffset + 16) return null;

        const x = isLittleEndian ? buf.readDoubleLE(coordOffset) : buf.readDoubleBE(coordOffset);
        const y = isLittleEndian ? buf.readDoubleLE(coordOffset + 8) : buf.readDoubleBE(coordOffset + 8);

        if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
        if (isUtm43n(x, y)) return [x, y];
      } catch {
        return null;
      }
    }
  }

  return null;
}
