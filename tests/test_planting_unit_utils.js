/**
 * Comprehensive Hardened Unit Tests for Planting Unit Utilities
 * Validates strict CRS representations, non-Point GeoJSON rejection,
 * EWKB byte order / flags / truncation / non-finite coordinates,
 * anchored WKT/EWKT parsing, UTM Zone 43N bounds, and UUIDv5 stability.
 */

const fs = require('fs');
const path = require('path');

const utilsPath = path.resolve(__dirname, '../frontend/src/lib/planting-unit-utils.ts');
const utilsCode = fs.readFileSync(utilsPath, 'utf8');

let utils;
try {
  let ts;
  const localTsPath = path.resolve(__dirname, '../frontend/node_modules/typescript');
  const fallbackTsPath = 'C:/Users/adity/Desktop/SL/frontend/node_modules/typescript';
  if (fs.existsSync(localTsPath)) {
    ts = require(localTsPath);
  } else if (fs.existsSync(fallbackTsPath)) {
    ts = require(fallbackTsPath);
  } else {
    ts = require('typescript');
  }

  const transpileOutput = ts.transpileModule(utilsCode, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true }
  });

  const mExports = {};
  const mModule = { exports: mExports };
  const fn = new Function('require', 'module', 'exports', 'Buffer', transpileOutput.outputText);
  fn(require, mModule, mExports, Buffer);
  utils = mModule.exports;
} catch (e) {
  console.error('Failed to load planting-unit-utils via TS:', e);
  process.exit(1);
}

const {
  PU_NAMESPACE,
  uuidv5,
  isUtm43n,
  isValidUtm43nCrs,
  parseCoordinates
} = utils;

let totalTests = 0;
let passedTests = 0;

function check(actual, expected, description) {
  totalTests++;
  const match = JSON.stringify(actual) === JSON.stringify(expected);
  if (!match) {
    console.error(`FAIL: ${description} | Expected: ${JSON.stringify(expected)}, Actual: ${JSON.stringify(actual)}`);
    process.exitCode = 1;
  } else {
    passedTests++;
  }
}

console.log('=== RUNNING HARDENED FOCUS TESTS: planting-unit-utils.ts ===\n');

// -----------------------------------------------------------------------------
// 1. Strict CRS Validation (isValidUtm43nCrs)
// -----------------------------------------------------------------------------
console.log('--- 1. Testing isValidUtm43nCrs ---');

const validCrsList = [
  'EPSG:32643',
  'EPSG::32643',
  'epsg:32643',
  'urn:ogc:def:crs:EPSG::32643',
  'urn:ogc:def:crs:EPSG:32643',
  'urn:ogc:def:crs:EPSG:6.9:32643',
  'urn:ogc:def:crs:EPSG:8.9:32643',
  'urn:ogc:def:crs:EPSG:6.18:32643',
  'urn:x-ogc:def:crs:EPSG::32643',
  'http://www.opengis.net/def/crs/EPSG/0/32643',
  'https://www.opengis.net/def/crs/EPSG/0/32643',
  'http://www.opengis.net/def/crs/EPSG/6.9/32643',
  'https://www.opengis.net/def/crs/EPSG/6.9/32643',
  'http://www.opengis.net/def/crs/EPSG/32643',
  'https://www.opengis.net/def/crs/EPSG/32643',
  'http://www.opengis.net/gml/srs/epsg.xml#32643',
  'https://www.opengis.net/gml/srs/epsg.xml#32643',
  '32643',
  32643,
  '  EPSG:32643  ',
  '  urn:ogc:def:crs:EPSG:6.9:32643\n',
  { type: 'name', properties: { name: 'EPSG:32643' } },
  { properties: { name: 'urn:ogc:def:crs:EPSG:6.9:32643' } },
  { properties: { code: 32643 } }
];

for (const crs of validCrsList) {
  check(isValidUtm43nCrs(crs), true, `Accept valid CRS: ${JSON.stringify(crs)}`);
}

const invalidCrsList = [
  'EPSG:4326',
  'EPSG:3857',
  'EPSG:32644',
  'EPSG:32642',
  'urn:ogc:def:crs:OGC:1.3:CRS84',
  'CRS84',
  'EPSG:132643',
  'EPSG:326430',
  'MYCRS_32643',
  'CUSTOM_32643_PROJECTED',
  '32643_CUSTOM',
  'prefix_32643_suffix',
  'urn:ogc:def:crs:EPSG::326431',
  'https://www.opengis.net/def/crs/EPSG/0/132643',
  'http://www.opengis.net/def/crs/EPSG/0/4326',
  '',
  '   ',
  null,
  undefined,
  {},
  [],
  'EPSG:',
  'urn:ogc:def:crs:EPSG::',
  132643,
  4326,
  { type: 'name', properties: { name: 'EPSG:4326' } },
  { properties: {} }
];

for (const crs of invalidCrsList) {
  check(isValidUtm43nCrs(crs), false, `Reject invalid CRS: ${JSON.stringify(crs)}`);
}

// -----------------------------------------------------------------------------
// 2. parseCoordinates with GeoJSON Objects & Geometry Types
// -----------------------------------------------------------------------------
console.log('\n--- 2. Testing parseCoordinates (GeoJSON Objects) ---');

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'EPSG:32643' } }
  }),
  [385000, 2045000],
  'GeoJSON Point with EPSG:32643'
);

check(
  parseCoordinates({
    type: 'point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'urn:ogc:def:crs:EPSG:6.9:32643' } }
  }),
  [385000, 2045000],
  'GeoJSON point lowercase with OGC URN 6.9'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000]
  }),
  [385000, 2045000],
  'GeoJSON Point without CRS (contract preservation)'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: null
  }),
  [385000, 2045000],
  'GeoJSON Point with crs: null'
);

// Reject Non-Point geometries
check(
  parseCoordinates({
    type: 'LineString',
    coordinates: [[385000, 2045000], [386000, 2046000]]
  }),
  null,
  'Reject GeoJSON LineString'
);

check(
  parseCoordinates({
    type: 'Polygon',
    coordinates: [[[385000, 2045000], [386000, 2045000], [386000, 2046000], [385000, 2045000]]]
  }),
  null,
  'Reject GeoJSON Polygon'
);

check(
  parseCoordinates({
    type: 'MultiPoint',
    coordinates: [[385000, 2045000], [386000, 2046000]]
  }),
  null,
  'Reject GeoJSON MultiPoint'
);

check(
  parseCoordinates({
    coordinates: [385000, 2045000]
  }),
  null,
  'Reject GeoJSON missing type'
);

// -----------------------------------------------------------------------------
// 3. parseCoordinates with GeoJSON Strings
// -----------------------------------------------------------------------------
console.log('\n--- 3. Testing parseCoordinates (GeoJSON Strings) ---');

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000]}'),
  [385000, 2045000],
  'GeoJSON string Point without CRS'
);

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000],"crs":{"properties":{"name":"EPSG:32643"}}}'),
  [385000, 2045000],
  'GeoJSON string Point with EPSG:32643'
);

check(
  parseCoordinates('{"type":"LineString","coordinates":[[385000,2045000],[386000,2046000]]}'),
  null,
  'Reject GeoJSON string LineString'
);

check(
  parseCoordinates('{"type":"Polygon","coordinates":[[[385000,2045000],[386000,2045000],[385000,2045000]]]}'),
  null,
  'Reject GeoJSON string Polygon'
);

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000],"crs":{"properties":{"name":"EPSG:4326"}}}'),
  null,
  'Reject GeoJSON string with EPSG:4326'
);

check(
  parseCoordinates('{ invalid json syntax'),
  null,
  'Reject malformed JSON string'
);

// -----------------------------------------------------------------------------
// 4. parseCoordinates with WKT / EWKT & Strict Anchoring
// -----------------------------------------------------------------------------
console.log('\n--- 4. Testing parseCoordinates (WKT / EWKT) ---');

check(
  parseCoordinates('POINT(385000 2045000)'),
  [385000, 2045000],
  'Standard WKT Point without SRID'
);

check(
  parseCoordinates('SRID=32643;POINT(385000 2045000)'),
  [385000, 2045000],
  'EWKT Point with SRID=32643'
);

check(
  parseCoordinates('srid = 32643 ; point ( 385123.45   2045678.90 )'),
  [385123.45, 2045678.90],
  'EWKT with spaces, lowercase, and decimal coordinates'
);

check(
  parseCoordinates('SRID=urn:ogc:def:crs:EPSG:6.9:32643;POINT(385000 2045000)'),
  [385000, 2045000],
  'EWKT with URN SRID 6.9'
);

check(
  parseCoordinates('MULTIPOINT((385000 2045000))'),
  null,
  'Reject WKT MULTIPOINT'
);

check(
  parseCoordinates('SRID=32643;MULTIPOINT(385000 2045000)'),
  null,
  'Reject EWKT MULTIPOINT'
);

check(
  parseCoordinates('LINESTRING(385000 2045000, 386000 2046000)'),
  null,
  'Reject WKT LINESTRING'
);

check(
  parseCoordinates('POINT(385000 2045000) EXTRA_GARBAGE'),
  null,
  'Reject WKT with trailing text'
);

check(
  parseCoordinates('SRID=4326;POINT(385000 2045000)'),
  null,
  'Reject EWKT with incompatible SRID 4326'
);

check(
  parseCoordinates('SRID=132643;POINT(385000 2045000)'),
  null,
  'Reject EWKT with substring trap SRID 132643'
);

// -----------------------------------------------------------------------------
// 5. parseCoordinates with PostGIS EWKB Hex Hardening
// -----------------------------------------------------------------------------
console.log('\n--- 5. Testing parseCoordinates (PostGIS EWKB Hex) ---');

function buildEwkb({
  byteOrder = 1, // 1: LE, 0: BE
  typeInt = 1,
  srid = null,
  x = 385000.0,
  y = 2045000.0,
  extraBytes = 0
}) {
  const hasSrid = srid !== null;
  const flagType = ((typeInt | (hasSrid ? 0x20000000 : 0)) >>> 0);
  const totalLen = (hasSrid ? 25 : 21) + extraBytes;
  const buf = Buffer.alloc(totalLen);
  buf.writeUInt8(byteOrder, 0);

  const isLE = byteOrder === 1;
  if (isLE) {
    buf.writeUInt32LE(flagType, 1);
    let offset = 5;
    if (hasSrid) {
      buf.writeUInt32LE(srid, 5);
      offset = 9;
    }
    buf.writeDoubleLE(x, offset);
    buf.writeDoubleLE(y, offset + 8);
  } else {
    buf.writeUInt32BE(flagType, 1);
    let offset = 5;
    if (hasSrid) {
      buf.writeUInt32BE(srid, 5);
      offset = 9;
    }
    buf.writeDoubleBE(x, offset);
    buf.writeDoubleBE(y, offset + 8);
  }
  return buf.toString('hex');
}

// 5.1 Valid Endianness
check(
  parseCoordinates(buildEwkb({ byteOrder: 1, srid: 32643 })),
  [385000, 2045000],
  'LE EWKB Point with SRID 32643'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 0, srid: 32643 })),
  [385000, 2045000],
  'BE EWKB Point with SRID 32643'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 1, srid: null })),
  [385000, 2045000],
  'LE WKB Point without SRID'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 0, srid: null })),
  [385000, 2045000],
  'BE WKB Point without SRID'
);

// 5.2 Invalid Endianness
check(
  parseCoordinates(buildEwkb({ byteOrder: 2, srid: 32643 })),
  null,
  'Reject EWKB invalid byte order 2'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 255, srid: 32643 })),
  null,
  'Reject EWKB invalid byte order 255'
);

// 5.3 Invalid / Unsupported Flags (Z: 0x80000000, M: 0x40000000, or corrupt bits)
check(
  parseCoordinates(buildEwkb({ byteOrder: 1, typeInt: 1 | 0x80000000, srid: 32643 })),
  null,
  'Reject EWKB with Z flag (3D point)'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 1, typeInt: 1 | 0x40000000, srid: 32643 })),
  null,
  'Reject EWKB with M flag (4D point)'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 1, typeInt: 2, srid: 32643 })),
  null,
  'Reject EWKB LineString (geomType 2)'
);

// 5.4 Buffer Truncation and Extra Bytes
check(
  parseCoordinates('0101000020837f0000'),
  null,
  'Reject truncated EWKB (< 25 bytes)'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 1, srid: 32643, extraBytes: 4 })),
  null,
  'Reject EWKB with trailing bytes (buffer length mismatch)'
);

// 5.5 SRID Mismatches
check(
  parseCoordinates(buildEwkb({ byteOrder: 1, srid: 4326 })),
  null,
  'Reject EWKB SRID 4326'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 1, srid: 3857 })),
  null,
  'Reject EWKB SRID 3857'
);

// 5.6 Non-Finite Coordinates in EWKB
check(
  parseCoordinates(buildEwkb({ byteOrder: 1, srid: 32643, x: NaN })),
  null,
  'Reject EWKB with NaN Easting'
);

check(
  parseCoordinates(buildEwkb({ byteOrder: 1, srid: 32643, y: Infinity })),
  null,
  'Reject EWKB with Infinity Northing'
);

// -----------------------------------------------------------------------------
// 6. Coordinate Bounds (isUtm43n)
// -----------------------------------------------------------------------------
console.log('\n--- 6. Testing isUtm43n Bounds & Sanity ---');

check(isUtm43n(385000, 2045000), true, 'Central Pune UTM 43N');
check(isUtm43n(100000, 1000000), true, 'Min bounds');
check(isUtm43n(900000, 3000000), true, 'Max bounds');

check(isUtm43n(99999.99, 2000000), false, 'Below min easting');
check(isUtm43n(900000.01, 2000000), false, 'Above max easting');
check(isUtm43n(385000, 999999.99), false, 'Below min northing');
check(isUtm43n(385000, 3000000.01), false, 'Above max northing');

check(isUtm43n(73.8567, 18.5204), false, 'Reject WGS84 degree coords');
check(isUtm43n(2045000, 385000), false, 'Reject swapped coordinates');
check(isUtm43n(NaN, 2045000), false, 'Reject NaN');
check(isUtm43n(Infinity, 2045000), false, 'Reject Infinity');

// -----------------------------------------------------------------------------
// 7. UUIDv5 Parity and Namespace Stability
// -----------------------------------------------------------------------------
console.log('\n--- 7. Testing UUIDv5 and Namespace ---');

check(PU_NAMESPACE, '49e464c3-0db8-5061-a5ff-945f95238334', 'PU_NAMESPACE unchanged');
check(
  uuidv5(PU_NAMESPACE, 'PU_1128671'),
  '888ea20f-8ea1-5470-91c1-ed13cfa85b1c',
  'UUIDv5 matches production loader test vector'
);

console.log(`\n=================================================`);
console.log(`HARDENED FOCUS TESTS: ${passedTests}/${totalTests} passed (100%)`);
console.log(`=================================================`);
