import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    MAPTILER_API_KEY: process.env.MAPTILER_API_KEY,
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Existing security headers
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },

          // HSTS: enforce HTTPS for 1 year, including subdomains
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains'
          },

          // Content-Security-Policy: built from actual UEHIS application dependencies
          //
          // Allowed domains:
          //   - MapTiler (tiles, fonts, API): api.maptiler.com
          //   - MapLibre GL JS (self, blob for workers)
          //   - Supabase (API, auth): 127.0.0.1:54321 and *.supabase.co
          //   - Geoapify (geocoding): api.geoapify.com
          //   - Google Fonts: fonts.googleapis.com, fonts.gstatic.com
          //   - Inline styles required for MapLibre
          //   - blob: required for MapLibre web workers
          //   - data: required for inline images/icons
          {
            key: 'Content-Security-Policy',
            value: [
              // Scripts: self + blob (MapLibre workers)
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:",
              // Styles: self + unsafe-inline (MapLibre injects styles) + Google Fonts
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              // Images: self + data URIs + MapTiler + blob + CartoCDN
              "img-src 'self' data: blob: https://api.maptiler.com https://*.maptiler.com https://basemaps.cartocdn.com https://*.cartocdn.com",
              // Fonts: self + Google Fonts + MapTiler
              "font-src 'self' https://fonts.gstatic.com https://api.maptiler.com",
              // Connect: self + Supabase + MapTiler + Geoapify + CartoCDN
              `connect-src 'self' http://127.0.0.1:54221 https://*.supabase.co https://api.maptiler.com https://*.maptiler.com https://api.geoapify.com https://basemaps.cartocdn.com https://*.cartocdn.com blob: ${process.env.NEXT_PUBLIC_SUPABASE_URL ? process.env.NEXT_PUBLIC_SUPABASE_URL : ''}`.trim(),
              // Workers: self + blob (MapLibre GL workers)
              "worker-src 'self' blob:",
              // Child/frame: none (no iframes needed)
              "frame-src 'none'",
              // Object: none
              "object-src 'none'",
              // Upgrade insecure requests in production
              ...(process.env.NODE_ENV === 'production' ? ["upgrade-insecure-requests"] : []),
              // Base URI: self
              "base-uri 'self'",
              // Form action: self
              "form-action 'self'",
              // Clickjacking protection: disallow framing
              "frame-ancestors 'none'",
            ].join('; ')
          },
        ],
      },
    ];
  },
};

export default nextConfig;
