# PMC GIS Service Audit

## 1. Website Accessibility and Application Structure
The official Pune Municipal Corporation GIS portal (`https://gis.pmc.gov.in/`) was investigated via a read-only technical audit to identify any publicly accessible geographic service layers.
* **Homepage/Portal:** The root URL serves a standard portal page.
* **Map Viewers:** Links labeled "City Map" (`/Account/GuestLogin`) and "Heritage Map" (`/Account/HeritageLogin`) instantly redirect to the secure login page (`/Account/Login`). 
* **Platform:** The application is explicitly marked as "Powered by IGiS" (Integrated GIS and Image Processing Software from SGL), an enterprise GIS platform, rather than a standard open-source stack like GeoServer.
* **JavaScript Bundles:** The public HTML includes only standard UI libraries (jQuery, Bootstrap, Camera Slider) and basic client-side logic (`custom.js`). A script for cryptographic functions (`AES.js`) is present on the login page. No mapping libraries (like Leaflet, OpenLayers, or ArcGIS API for JS) or configuration files exposing service URLs are loaded prior to authentication.

## 2. Public Service Discovery
An active probe of common standard GIS service patterns was conducted.
* `/arcgis/rest/services`
* `/server/rest/services`
* `/geoserver/wfs`
* `/geoserver/wms`
* `/api/`
* `/map/`
* `/CityMap`
* `/webgis`

**Result:** Every probed path either returned a custom 404 Error page or enforced an HTTP redirect (302) to the `/Account/Login` page. 

## 3. Layer Metadata and Administrative-vs-Electoral Classification
* **Service URLs Discovered:** None.
* **Layer Metadata:** None available. 
* **Classification:** Because the underlying data services are unreachable without authentication, it is impossible to publicly interrogate the platform to classify its layers (administrative wards vs. electoral wards) or view fields, geometry types, and coordinate reference systems. 
* **Authentication Status:** **Strict.** The map-layer access and the website viewer both require a valid, authenticated session. The platform actively guards all geographic endpoints.

## 4. Current Geometry Queryability
* **Administrative Wards:** The current PMC administrative ward geometry is **not** publicly queryable via this portal.
* **Municipal Boundary:** The current PMC municipal boundary geometry is **not** publicly queryable via this portal.

## 5. Exact Remaining Blocker
The fundamental blocker is **closed-system access control**. The PMC GIS portal strictly enforces authentication for all map viewer paths and does not expose open standard REST or WFS/WMS endpoints to the unauthenticated internet. There is no technical mechanism to safely, legally, or technically extract the ward geometry without authorized credentials.

---

## Final Answers

**A. Did you find a public current PMC administrative ward layer?**
No.

**B. Did you find a public current PMC municipal boundary layer?**
No.

**C. Can UEHIS legally/technically retrieve it without authentication?**
No. The geographic services and map viewers are entirely hidden behind an authentication wall. Even the `GuestLogin` redirects to the standard Login page, blocking all public access to the map layers and API endpoints.

**D. If yes, provide the exact service/layer endpoint for later controlled ingestion.**
N/A

**E. If no, state exactly what manual/official request is required.**
An official request must be submitted directly to the PMC GIS Cell to explicitly release the current 15-ward administrative shapefiles (encompassing the 518 km² post-2021 merger extent). Alternatively, the project stakeholders must provision a registered account with valid API credentials to allow a secure, authenticated connection to the PMC IGiS platform.
