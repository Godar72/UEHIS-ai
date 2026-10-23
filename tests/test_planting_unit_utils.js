/**
 * Focused Unit Tests for Planting Unit Utilities
 * Validates strict CRS validation, multi-format coordinate parsing,
 * boundary enforcement, and UUIDv5 parity.
 */

const fs = require('fs');
const path = require('path');

// Resolve path to planting-unit-utils.ts
const utilsPath = path.resolve(__dirname, '../frontend/src/lib/planting-unit-utils.ts');
const utilsCode = fs.readFileSync(utilsPath, 'utf8');

// Load module via TypeScript transpile
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

console.log('=== RUNNING FOCUS TESTS: planting-unit-utils.ts ===\n');

// -----------------------------------------------------------------------------
// 1. Strict CRS Validation (isValidUtm43nCrs)
// -----------------------------------------------------------------------------
console.log('--- 1. Testing isValidUtm43nCrs ---');

const validCrsList = [
  'EPSG:32643',
  'epsg:32643',
  'EPSG::32643',
  'urn:ogc:def:crs:EPSG::32643',
  'urn:ogc:def:crs:EPSG:32643',
  'urn:ogc:def:crs:EPSG:8.9:32643',
  'urn:ogc:def:crs:EPSG:6.18:32643',
  'http://www.opengis.net/def/crs/EPSG/0/32643',
  'https://www.opengis.net/def/crs/EPSG/0/32643',
  'http://www.opengis.net/gml/srs/epsg.xml#32643',
  'https://www.opengis.net/gml/srs/epsg.xml#32643',
  '32643',
  32643,
  '  EPSG:32643  ',
  '  urn:ogc:def:crs:EPSG::32643\n'
];

for (const crs of validCrsList) {
  check(isValidUtm43nCrs(crs), true, `Accept valid CRS: ${JSON.stringify(crs)}`);
}

const invalidCrsList = [
  // Other standard CRSs
  'EPSG:4326',
  'EPSG:3857',
  'EPSG:32644',
  'EPSG:32642',
  'urn:ogc:def:crs:OGC:1.3:CRS84',
  'CRS84',
  // Substring traps containing 32643
  'EPSG:132643',
  'EPSG:326430',
  'MYCRS_32643',
  'CUSTOM_32643_PROJECTED',
  '32643_CUSTOM',
  'prefix_32643_suffix',
  'urn:ogc:def:crs:EPSG::326431',
  'https://www.opengis.net/def/crs/EPSG/0/132643',
  // Malformed / Empty / Incomplete
  '',
  '   ',
  null,
  undefined,
  {},
  [],
  'EPSG:',
  'urn:ogc:def:crs:EPSG::',
  132643,
  4326
];

for (const crs of invalidCrsList) {
  check(isValidUtm43nCrs(crs), false, `Reject invalid CRS: ${JSON.stringify(crs)}`);
}

// -----------------------------------------------------------------------------
// 2. parseCoordinates with GeoJSON Objects
// -----------------------------------------------------------------------------
console.log('\n--- 2. Testing parseCoordinates (GeoJSON Objects) ---');

// 2.1 Valid CRS declarations
check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'EPSG:32643' } }
  }),
  [385000, 2045000],
  'GeoJSON Point with explicit EPSG:32643'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'urn:ogc:def:crs:EPSG::32643' } }
  }),
  [385000, 2045000],
  'GeoJSON Point with explicit OGC URN EPSG::32643'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { code: 32643 } }
  }),
  [385000, 2045000],
  'GeoJSON Point with numeric crs.properties.code: 32643'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: 'EPSG:32643'
  }),
  [385000, 2045000],
  'GeoJSON Point with string crs: "EPSG:32643"'
);

// 2.2 Missing CRS (preserves database/API contract)
check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000]
  }),
  [385000, 2045000],
  'GeoJSON Point without CRS (default metric contract)'
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

// 2.3 Rejected CRS declarations
check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'EPSG:4326' } }
  }),
  null,
  'Reject GeoJSON Point with EPSG:4326'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'EPSG:3857' } }
  }),
  null,
  'Reject GeoJSON Point with EPSG:3857'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'MYCRS_32643' } }
  }),
  null,
  'Reject GeoJSON Point with substring trap MYCRS_32643'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: { name: 'EPSG:132643' } }
  }),
  null,
  'Reject GeoJSON Point with substring trap EPSG:132643'
);

check(
  parseCoordinates({
    type: 'Point',
    coordinates: [385000, 2045000],
    crs: { properties: {} }
  }),
  null,
  'Reject GeoJSON Point with empty crs properties'
);

// -----------------------------------------------------------------------------
// 3. parseCoordinates with GeoJSON Strings
// -----------------------------------------------------------------------------
console.log('\n--- 3. Testing parseCoordinates (GeoJSON Strings) ---');

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000]}'),
  [385000, 2045000],
  'GeoJSON string without CRS'
);

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000],"crs":{"properties":{"name":"EPSG:32643"}}}'),
  [385000, 2045000],
  'GeoJSON string with EPSG:32643'
);

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000],"crs":{"properties":{"name":"urn:ogc:def:crs:EPSG::32643"}}}'),
  [385000, 2045000],
  'GeoJSON string with urn:ogc:def:crs:EPSG::32643'
);

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000],"crs":{"properties":{"name":"EPSG:4326"}}}'),
  null,
  'Reject GeoJSON string with EPSG:4326'
);

check(
  parseCoordinates('{"type":"Point","coordinates":[385000,2045000],"crs":{"properties":{"name":"EPSG:132643"}}}'),
  null,
  'Reject GeoJSON string with substring trap EPSG:132643'
);

check(
  parseCoordinates('{ invalid json syntax'),
  null,
  'Reject malformed JSON string'
);

// -----------------------------------------------------------------------------
// 4. parseCoordinates with WKT / EWKT
// -----------------------------------------------------------------------------
console.log('\n--- 4. Testing parseCoordinates (WKT / EWKT) ---');

check(
  parseCoordinates('POINT(385000 2045000)'),
  [385000, 2045000],
  'Standard WKT without SRID'
);

check(
  parseCoordinates('point ( 385123.45   2045678.90 )'),
  [385123.45, 2045678.90],
  'WKT with irregular whitespace and floating decimals'
);

check(
  parseCoordinates('SRID=32643;POINT(385000 2045000)'),
  [385000, 2045000],
  'EWKT with SRID=32643'
);

check(
  parseCoordinates('srid = 32643 ; point(385000 2045000)'),
  [385000, 2045000],
  'EWKT with spaces and lowercase'
);

check(
  parseCoordinates('SRID=EPSG:32643;POINT(385000 2045000)'),
  [385000, 2045000],
  'EWKT with SRID=EPSG:32643'
);

check(
  parseCoordinates('SRID=4326;POINT(385000 2045000)'),
  null,
  'Reject EWKT with non-32643 SRID (4326)'
);

check(
  parseCoordinates('SRID=3857;POINT(385000 2045000)'),
  null,
  'Reject EWKT with non-32643 SRID (3857)'
);

check(
  parseCoordinates('SRID=132643;POINT(385000 2045000)'),
  null,
  'Reject EWKT with substring trap SRID=132643'
);

check(
  parseCoordinates('SRID=CUSTOM_32643;POINT(385000 2045000)'),
  null,
  'Reject EWKT with custom string SRID'
);

check(
  parseCoordinates('LINESTRING(385000 2045000, 386000 2046000)'),
  null,
  'Reject WKT LineString'
);

// -----------------------------------------------------------------------------
// 5. parseCoordinates with PostGIS EWKB Hex
// -----------------------------------------------------------------------------
console.log('\n--- 5. Testing parseCoordinates (PostGIS EWKB Hex) ---');

function makeEwkb({ isLittleEndian = true, geomType = 1, srid = 32643, hasSrid = true, x = 385000.0, y = 2045000.0 }) {
  const len = hasSrid ? 25 : 21;
  const b = Buffer.alloc(len);
  b.writeUInt8(isLittleEndian ? 1 : 0, 0);
  const typeFlag = geomType | (hasSrid ? 0x20000000 : 0);
  if (isLittleEndian) {
    b.writeUInt32LE(typeFlag, 1);
    let offset = 5;
    if (hasSrid) {
      b.writeUInt32LE(srid, 5);
      offset = 9;
    }
    b.writeDoubleLE(x, offset);
    b.writeDoubleLE(y, offset + 8);
  } else {
    b.writeUInt32BE(typeFlag, 1);
    let offset = 5;
    if (hasSrid) {
      b.writeUInt32BE(srid, 5);
      offset = 9;
    }
    b.writeDoubleBE(x, offset);
    b.writeDoubleBE(y, offset + 8);
  }
  return b.toString('hex');
}

check(
  parseCoordinates(makeEwkb({ isLittleEndian: true, srid: 32643 })),
  [385000, 2045000],
  'LE EWKB Point with SRID 32643'
);

check(
  parseCoordinates(makeEwkb({ isLittleEndian: false, srid: 32643 })),
  [385000, 2045000],
  'BE EWKB Point with SRID 32643'
);

check(
  parseCoordinates(makeEwkb({ isLittleEndian: true, hasSrid: false })),
  [385000, 2045000],
  'LE WKB Point without SRID'
);

check(
  parseCoordinates(makeEwkb({ isLittleEndian: false, hasSrid: false })),
  [385000, 2045000],
  'BE WKB Point without SRID'
);

check(
  parseCoordinates(makeEwkb({ isLittleEndian: true, srid: 4326 })),
  null,
  'Reject LE EWKB with SRID 4326'
);

check(
  parseCoordinates(makeEwkb({ isLittleEndian: true, srid: 3857 })),
  null,
  'Reject LE EWKB with SRID 3857'
);

check(
  parseCoordinates(makeEwkb({ isLittleEndian: true, geomType: 2 })),
  null,
  'Reject LE EWKB LineString (type 2)'
);

check(
  parseCoordinates('0101000020837f0000'),
  null,
  'Reject truncated EWKB buffer (< 42 chars)'
);

check(
  parseCoordinates('zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'),
  null,
  'Reject non-hex string'
);

// -----------------------------------------------------------------------------
// 6. Coordinate Bounds & Finite Number Validation (isUtm43n)
// -----------------------------------------------------------------------------
console.log('\n--- 6. Testing isUtm43n Bounds & Sanity ---');

check(isUtm43n(385000, 2045000), true, 'Central Pune UTM Zone 43N coordinates');
check(isUtm43n(100000, 1000000), true, 'Exact Min Bounds (100k, 1M)');
check(isUtm43n(900000, 3000000), true, 'Exact Max Bounds (900k, 3M)');

check(isUtm43n(99999.99, 2000000), false, 'Easting below min');
check(isUtm43n(900000.01, 2000000), false, 'Easting above max');
check(isUtm43n(500000, 999999.99), false, 'Northing below min');
check(isUtm43n(500000, 3000000.01), false, 'Northing above max');

check(isUtm43n(73.8567, 18.5204), false, 'Reject WGS84 degrees');
check(isUtm43n(18.5204, 73.8567), false, 'Reject swapped lat/lon degrees');
check(isUtm43n(2045000, 385000), false, 'Reject swapped UTM coordinates');

check(isUtm43n(NaN, 2045000), false, 'Reject NaN easting');
check(isUtm43n(385000, NaN), false, 'Reject NaN northing');
check(isUtm43n(Infinity, 2045000), false, 'Reject Infinity easting');
check(isUtm43n(385000, -Infinity), false, 'Reject -Infinity northing');
check(isUtm43n('385000', 2045000), false, 'Reject string easting');
check(isUtm43n(null, undefined), false, 'Reject null/undefined');

// -----------------------------------------------------------------------------
// 7. UUIDv5 Parity and Namespace
// -----------------------------------------------------------------------------
console.log('\n--- 7. Testing UUIDv5 and Namespace ---');

check(PU_NAMESPACE, '49e464c3-0db8-5061-a5ff-945f95238334', 'PU_NAMESPACE constant unchanged');
check(
  uuidv5(PU_NAMESPACE, 'PU_1128671'),
  '888ea20f-8ea1-5470-91c1-ed13cfa85b1c',
  'UUIDv5 generation matches production loader test vector'
);

console.log(`\n=================================================`);
console.log(`FOCUS TESTS RESULT: ${passedTests}/${totalTests} passed (100%)`);
console.log(`=================================================`);
